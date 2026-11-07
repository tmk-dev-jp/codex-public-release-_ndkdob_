"""Strict JSON configuration loading for experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dl_research.exceptions import ConfigError
from dl_research.experiment.comparison import validate_comparison

Stage = Literal["smoke", "pilot", "full"]
CheckpointMode = Literal["min"]
ReviewMode = Literal["local", "independent"]
MetricDirection = Literal["maximize", "minimize"]
DecisionMode = Literal["threshold", "trend"]


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be an object")
    return value


def _string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ConfigError(f"{name} must be a non-empty string")
    return value


def _integer(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return value


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be numeric")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return result


def _optional_limit(value: Any, name: str) -> int | None:
    if value is None:
        return None
    return _integer(value, name, minimum=1)


@dataclass(frozen=True)
class ExperimentIdentity:
    id: str
    stage: Stage
    seed: int
    deterministic: bool
    review_mode: ReviewMode
    output_dir: str
    baseline_id: str | None
    queue_id: str | None


@dataclass(frozen=True)
class DecisionConfig:
    primary_metric: str
    direction: MetricDirection
    mode: DecisionMode
    minimum_effect: float | None


@dataclass(frozen=True)
class DataConfig:
    name: str
    batch_size: int
    num_workers: int
    parameters: dict[str, Any]
    seed: int | None = None


@dataclass(frozen=True)
class ModelConfig:
    name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class OptimizerConfig:
    name: str
    learning_rate: float
    weight_decay: float
    momentum: float


@dataclass(frozen=True)
class TrainConfig:
    epochs: int
    device: str
    optimizer: OptimizerConfig
    loss: str
    amp: bool
    gradient_clip_norm: float | None
    early_stopping_patience: int
    max_train_batches: int | None
    max_validation_batches: int | None
    checkpoint_metric: str
    checkpoint_mode: CheckpointMode


@dataclass(frozen=True)
class TestConfig:
    device: str
    max_batches: int | None
    checkpoint: str


@dataclass(frozen=True)
class ExperimentConfig:
    schema_version: str
    experiment: ExperimentIdentity
    decision: DecisionConfig
    data: DataConfig
    model: ModelConfig
    train: TrainConfig
    test: TestConfig
    source_path: Path
    comparison: dict[str, Any] | None = None


def load_config(path: str | Path) -> ExperimentConfig:
    source = Path(path).expanduser().resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {source}: line {exc.lineno}") from exc

    root = _mapping(raw, "config")
    schema_version = _string(root.get("schema_version", "2.0"), "schema_version")

    exp_raw = _mapping(root.get("experiment"), "experiment")
    stage = _string(exp_raw.get("stage"), "experiment.stage")
    if stage not in {"smoke", "pilot", "full"}:
        raise ConfigError("experiment.stage must be smoke, pilot, or full")
    review_mode = _string(exp_raw.get("review_mode", "local"), "experiment.review_mode")
    if review_mode not in {"local", "independent"}:
        raise ConfigError("experiment.review_mode must be local or independent")
    deterministic = exp_raw.get("deterministic", True)
    if not isinstance(deterministic, bool):
        raise ConfigError("experiment.deterministic must be boolean")
    baseline = exp_raw.get("baseline_id")
    queue_id = exp_raw.get("queue_id")
    if baseline is not None:
        baseline = _string(baseline, "experiment.baseline_id")
    if queue_id is not None:
        queue_id = _string(queue_id, "experiment.queue_id")
    experiment = ExperimentIdentity(
        id=_string(exp_raw.get("id"), "experiment.id"),
        stage=stage,
        seed=_integer(exp_raw.get("seed", 42), "experiment.seed", minimum=0),
        deterministic=deterministic,
        review_mode=review_mode,
        output_dir=_string(exp_raw.get("output_dir"), "experiment.output_dir"),
        baseline_id=baseline,
        queue_id=queue_id,
    )

    decision_raw = _mapping(root.get("decision", {}), "decision")
    direction = _string(decision_raw.get("direction", "maximize"), "decision.direction")
    if direction not in {"maximize", "minimize"}:
        raise ConfigError("decision.direction must be maximize or minimize")
    mode = _string(decision_raw.get("mode", "threshold"), "decision.mode")
    if mode not in {"threshold", "trend"}:
        raise ConfigError("decision.mode must be threshold or trend")
    raw_minimum_effect = decision_raw.get("minimum_effect", 0.0)
    if mode == "threshold":
        minimum_effect = _number(
            raw_minimum_effect,
            "decision.minimum_effect",
            minimum=0.0,
        )
    else:
        if raw_minimum_effect is not None:
            raise ConfigError("decision.minimum_effect must be null in trend mode")
        minimum_effect = None
    decision = DecisionConfig(
        primary_metric=_string(
            decision_raw.get("primary_metric", "test_accuracy"),
            "decision.primary_metric",
        ),
        direction=direction,
        mode=mode,
        minimum_effect=minimum_effect,
    )

    data_raw = _mapping(root.get("data"), "data")
    data = DataConfig(
        name=_string(data_raw.get("name"), "data.name"),
        batch_size=_integer(data_raw.get("batch_size", 32), "data.batch_size", minimum=1),
        num_workers=_integer(data_raw.get("num_workers", 0), "data.num_workers", minimum=0),
        parameters=_mapping(data_raw.get("parameters", {}), "data.parameters"),
        seed=(None if "seed" not in data_raw else
              _integer(data_raw["seed"], "data.seed", minimum=0)),
    )

    model_raw = _mapping(root.get("model"), "model")
    model = ModelConfig(
        name=_string(model_raw.get("name"), "model.name"),
        parameters=_mapping(model_raw.get("parameters", {}), "model.parameters"),
    )

    train_raw = _mapping(root.get("train"), "train")
    optimizer_raw = _mapping(train_raw.get("optimizer"), "train.optimizer")
    optimizer = OptimizerConfig(
        name=_string(optimizer_raw.get("name", "adamw"), "train.optimizer.name"),
        learning_rate=_number(
            optimizer_raw.get("learning_rate", 1e-3),
            "train.optimizer.learning_rate",
            minimum=0.0,
        ),
        weight_decay=_number(
            optimizer_raw.get("weight_decay", 0.0),
            "train.optimizer.weight_decay",
            minimum=0.0,
        ),
        momentum=_number(
            optimizer_raw.get("momentum", 0.9),
            "train.optimizer.momentum",
            minimum=0.0,
        ),
    )
    amp = train_raw.get("amp", False)
    if not isinstance(amp, bool):
        raise ConfigError("train.amp must be boolean")
    clip = train_raw.get("gradient_clip_norm")
    if clip is not None:
        clip = _number(clip, "train.gradient_clip_norm", minimum=0.0)
    if "early_stopping_patience" not in train_raw or train_raw.get(
        "early_stopping_patience"
    ) is None:
        raise ConfigError("train.early_stopping_patience is required")
    patience = _integer(
        train_raw.get("early_stopping_patience"),
        "train.early_stopping_patience",
        minimum=0,
    )
    checkpoint_mode = _string(
        train_raw.get("checkpoint_mode", "min"), "train.checkpoint_mode"
    )
    if checkpoint_mode != "min":
        raise ConfigError(
            "train.checkpoint_mode must be min for validation-loss checkpointing"
        )
    checkpoint_metric = _string(
        train_raw.get("checkpoint_metric", "loss"), "train.checkpoint_metric"
    )
    if checkpoint_metric != "loss":
        raise ConfigError(
            "train.checkpoint_metric must be loss for validation-loss checkpointing"
        )
    train = TrainConfig(
        epochs=_integer(train_raw.get("epochs", 1), "train.epochs", minimum=1),
        device=_string(train_raw.get("device", "auto"), "train.device"),
        optimizer=optimizer,
        loss=_string(train_raw.get("loss", "cross_entropy"), "train.loss"),
        amp=amp,
        gradient_clip_norm=clip,
        early_stopping_patience=patience,
        max_train_batches=_optional_limit(
            train_raw.get("max_train_batches"), "train.max_train_batches"
        ),
        max_validation_batches=_optional_limit(
            train_raw.get("max_validation_batches"), "train.max_validation_batches"
        ),
        checkpoint_metric=checkpoint_metric,
        checkpoint_mode=checkpoint_mode,
    )

    test_raw = _mapping(root.get("test"), "test")
    test = TestConfig(
        device=_string(test_raw.get("device", "auto"), "test.device"),
        max_batches=_optional_limit(test_raw.get("max_batches"), "test.max_batches"),
        checkpoint=_string(test_raw.get("checkpoint", "best.pt"), "test.checkpoint"),
    )

    return ExperimentConfig(
        schema_version=schema_version,
        experiment=experiment,
        decision=decision,
        data=data,
        model=model,
        train=train,
        test=test,
        source_path=source,
        comparison=validate_comparison(root),
    )
