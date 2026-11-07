from __future__ import annotations

import copy
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
SRC = _REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dl_research.config import ExperimentConfig, load_config
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.records import plan_hash
from scripts.workflow import experiment_manifest_path, require_active

CONTROL_FILE = "research/TRAINING_CONTROLS.json"
LR_LADDERS = {
    "adamw": [0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001],
    "sgd": [1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001],
}
MAX_LOSS_GROWTH = 4.0


def _torch():
    import torch

    return torch


def _with_controls(config: ExperimentConfig, *, batch_size: int, learning_rate: float) -> ExperimentConfig:
    data = replace(config.data, batch_size=batch_size)
    optimizer = replace(config.train.optimizer, learning_rate=learning_rate)
    train = replace(config.train, optimizer=optimizer)
    return replace(config, data=data, train=train)


def _finite_parameters(model: Any) -> bool:
    torch = _torch()
    return all(torch.isfinite(parameter).all() for parameter in model.parameters())


def _probe(config: ExperimentConfig, *, batch_size: int, learning_rate: float, steps: int) -> bool:
    torch = _torch()
    from dl_research.data.factory import build_data_loader
    from dl_research.models.factory import build_model
    from dl_research.runtime import resolve_device, seed_everything
    from dl_research.training.factory import build_loss, build_optimizer

    candidate = _with_controls(config, batch_size=batch_size, learning_rate=learning_rate)
    seed_everything(candidate.experiment.seed, candidate.experiment.deterministic)
    device = resolve_device(candidate.train.device)
    data_seed = candidate.experiment.seed if candidate.data.seed is None else candidate.data.seed
    data_loader = build_data_loader(candidate.data, seed=data_seed)
    data_loader.setup()
    model = build_model(candidate.model)
    model.to(device)
    loss_fn = build_loss(candidate.train.loss)
    optimizer = build_optimizer(model, candidate.train.optimizer)
    iterator = iter(data_loader.train_loader())
    first_loss: float | None = None
    max_loss = 0.0
    completed = 0
    for _ in range(steps):
        try:
            inputs, targets = next(iterator)
        except StopIteration:
            break
        inputs = inputs.to(device)
        targets = targets.to(device)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(inputs)
        loss = loss_fn(outputs, targets)
        if not torch.isfinite(loss):
            raise FloatingPointError("non-finite probe loss")
        loss_value = float(loss.detach())
        if first_loss is None:
            first_loss = loss_value
        max_loss = max(max_loss, loss_value)
        loss.backward()
        gradients = [
            parameter.grad
            for parameter in model.parameters()
            if parameter.requires_grad and parameter.grad is not None
        ]
        if not gradients or not all(torch.isfinite(gradient).all() for gradient in gradients):
            raise FloatingPointError("non-finite probe gradients")
        if candidate.train.gradient_clip_norm is not None:
            torch.nn.utils.clip_grad_norm_(model.parameters(), candidate.train.gradient_clip_norm)
        optimizer.step()
        if not _finite_parameters(model):
            raise FloatingPointError("non-finite probe parameters")
        completed += 1
    if completed == 0 or first_loss is None:
        raise RuntimeError("training loader produced no probe batches")
    return max_loss <= max(first_loss * MAX_LOSS_GROWTH, first_loss + 1e-8)


def _train_size(config: ExperimentConfig) -> int:
    from dl_research.data.factory import build_data_loader

    data_seed = config.experiment.seed if config.data.seed is None else config.data.seed
    data_loader = build_data_loader(config.data, seed=data_seed)
    data_loader.setup()
    metadata = data_loader.metadata()
    split_sizes = metadata.get("split_sizes", {})
    size = split_sizes.get("train")
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("data loader metadata must provide positive split_sizes.train")
    return size


def _powers_of_two(maximum: int) -> list[int]:
    value = 1
    result: list[int] = []
    while value <= maximum:
        result.append(value)
        value *= 2
    return list(reversed(result))


def _margin_power(value: int) -> int:
    if value <= 2:
        return value
    return 2 ** max(0, int(math.log2(value)) - 1)


def _margin_lr(ladder: list[float], value: float) -> float:
    index = ladder.index(value)
    return ladder[index + 1] if index + 1 < len(ladder) else value


def _probe_status(
    config: ExperimentConfig,
    *,
    batch_size: int,
    learning_rate: float,
    steps: int,
) -> tuple[bool, str | None]:
    try:
        passed = _probe(
            config,
            batch_size=batch_size,
            learning_rate=learning_rate,
            steps=steps,
        )
    except (RuntimeError, FloatingPointError, ValueError, OverflowError) as exc:
        torch = _torch()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return False, type(exc).__name__
    torch = _torch()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return passed, None


def _calibrate(config: ExperimentConfig) -> dict[str, Any]:
    if config.experiment.stage not in {"smoke", "pilot"}:
        raise ValueError("only smoke and pilot stages may be calibrated automatically")
    optimizer_name = config.train.optimizer.name
    ladder = LR_LADDERS.get(optimizer_name)
    if ladder is None:
        raise ValueError(f"no deterministic learning-rate ladder for optimizer: {optimizer_name}")
    steps = 2 if config.experiment.stage == "smoke" else 4
    train_size = _train_size(config)
    safe_lr = ladder[-1]

    batch_candidates = _powers_of_two(train_size)
    batch_results: list[dict[str, Any]] = []
    largest_batch = None
    for batch_size in batch_candidates:
        passed, error_type = _probe_status(
            config,
            batch_size=batch_size,
            learning_rate=safe_lr,
            steps=1,
        )
        batch_results.append(
            {"value": batch_size, "status": "passed" if passed else "failed", "error_type": error_type}
        )
        if passed:
            largest_batch = batch_size
            break
    if largest_batch is None:
        raise RuntimeError("no batch-size candidate passed the deterministic probe")
    selected_batch = _margin_power(largest_batch)

    lr_results: list[dict[str, Any]] = []
    largest_lr = None
    for learning_rate in ladder:
        passed, error_type = _probe_status(
            config,
            batch_size=selected_batch,
            learning_rate=learning_rate,
            steps=steps,
        )
        lr_results.append(
            {"value": learning_rate, "status": "passed" if passed else "failed", "error_type": error_type}
        )
        if passed:
            largest_lr = learning_rate
            break
    if largest_lr is None:
        raise RuntimeError("no learning-rate candidate passed the deterministic probe")
    selected_lr = _margin_lr(ladder, largest_lr)

    passed, error_type = _probe_status(
        config,
        batch_size=selected_batch,
        learning_rate=selected_lr,
        steps=steps,
    )
    if not passed:
        raise RuntimeError(f"selected controls failed validation probe: {error_type}")

    return {
        "status": "calibrated",
        "batch_size": selected_batch,
        "learning_rate": selected_lr,
        "raw_largest_passing_batch_size": largest_batch,
        "raw_largest_stable_learning_rate": largest_lr,
        "probe_steps": steps,
        "max_loss_growth": MAX_LOSS_GROWTH,
        "batch_candidates": batch_results,
        "learning_rate_candidates": lr_results,
    }


def _apply_to_config(config_path: Path, *, batch_size: int, learning_rate: float) -> bool:
    payload = read_json(config_path)
    original = copy.deepcopy(payload)
    payload["data"]["batch_size"] = batch_size
    payload["train"]["optimizer"]["learning_rate"] = learning_rate
    if payload == original:
        return False
    atomic_write_json(config_path, payload)
    return True


def _refresh_locked_hashes(root: Path, experiment_id: str, manifest: dict[str, Any]) -> None:
    active = root / "experiments/active" / experiment_id
    record_path = active / "EXPERIMENT.md"
    scope_path = active / "SCOPE.json"
    config_path = root / manifest["config"]
    manifest["plan_sha256"] = plan_hash(record_path, config_path, scope_path)
    manifest["locked_config_sha256"] = sha256_file(config_path)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)


def tune_training_controls(root: Path, experiment_id: str) -> dict[str, Any]:
    state, manifest = require_active(root, experiment_id, {"DRAFT", "PLANNED", "FAILED"})
    config_path = root / manifest["config"]
    if state.get("phase") in {"PLANNED", "FAILED"}:
        active = root / "experiments/active" / experiment_id
        if plan_hash(
            active / "EXPERIMENT.md",
            config_path,
            active / "SCOPE.json",
        ) != manifest.get("plan_sha256"):
            raise ValueError(
                "locked plan, config, or scope changed before calibration"
            )
        if sha256_file(config_path) != manifest.get("locked_config_sha256"):
            raise ValueError("config changed after plan locking")
    config = load_config(config_path)
    controls_path = root / CONTROL_FILE
    controls = read_json(controls_path)
    stages = controls.setdefault("stages", {})
    stage = config.experiment.stage
    stage_controls = stages.get(stage)

    if isinstance(stage_controls, dict) and stage_controls.get("status") == "locked":
        selected = {
            "status": "reused_locked",
            "batch_size": int(stage_controls["batch_size"]),
            "learning_rate": float(stage_controls["learning_rate"]),
        }
    else:
        selected = _calibrate(config)
        stages[stage] = {
            "status": "locked",
            "batch_size": selected["batch_size"],
            "learning_rate": selected["learning_rate"],
            "source_experiment_id": experiment_id,
            "optimizer": config.train.optimizer.name,
            "seed": config.experiment.seed,
        }
        atomic_write_json(controls_path, controls)

    changed = _apply_to_config(
        config_path,
        batch_size=int(selected["batch_size"]),
        learning_rate=float(selected["learning_rate"]),
    )
    report = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "stage": stage,
        "phase": state.get("phase"),
        "config_changed": changed,
        "controls": selected,
        "global_controls": CONTROL_FILE,
        "comparison_rule": "Use the same locked stage controls for final comparisons.",
    }
    report_path = root / "experiments/active" / experiment_id / "TRAINING_CONTROLS.json"
    atomic_write_json(report_path, report)
    manifest["training_controls"] = report_path.relative_to(root).as_posix()
    if state.get("phase") in {"PLANNED", "FAILED"}:
        _refresh_locked_hashes(root, experiment_id, manifest)
    else:
        atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    return report


def _execute() -> str:
    parser = QuietArgumentParser(description="Deterministically calibrate or apply training controls.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    report = tune_training_controls(root, args.experiment_id)
    controls = report["controls"]
    return (
        f"{args.experiment_id} stage={report['stage']} "
        f"batch_size={controls['batch_size']} learning_rate={controls['learning_rate']}"
    )


if __name__ == "__main__":
    raise SystemExit(run_script("tune-training-controls", _execute))
