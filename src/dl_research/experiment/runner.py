"""Compose data, model, trainer, and tester into compact experiment artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from dl_research.config import ExperimentConfig, load_config
from dl_research.data.factory import build_data_loader
from dl_research.evaluation.tester import Tester
from dl_research.experiment.policy import enforce_execution_policy
from dl_research.models.factory import build_model
from dl_research.runtime import (
    atomic_write_json,
    config_sha256,
    environment_manifest,
    find_project_root,
    relative_path,
    resolve_device,
    seed_everything,
)
from dl_research.training.factory import build_loss, build_optimizer
from dl_research.training.trainer import Trainer


class ExperimentRunner:
    """Run silent sanity, training, and aggregate evaluation operations."""

    def __init__(self, config: ExperimentConfig, *, root: Path | None = None) -> None:
        self.config = config
        self.root = (root or find_project_root(config.source_path)).resolve()
        self.output_dir = self._resolve_output_dir(config.experiment.output_dir)

    @classmethod
    def from_path(
        cls, config_path: str | Path, *, root: Path | None = None
    ) -> "ExperimentRunner":
        return cls(load_config(config_path), root=root)

    def _resolve_output_dir(self, value: str) -> Path:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("experiment output_dir must remain inside the repository") from exc
        return candidate

    def _prepare_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        agents = self.output_dir / "AGENTS.md"
        if not agents.exists():
            agents.write_text(
                "# Result scope\n\n"
                "- Read `metrics.json`, `manifest.json`, and failure-only `error.json`.\n"
                "- Do not inspect checkpoints or edit generated artifacts by default.\n"
                "- Do not create histories, logs, tensor dumps, or derived reports here.\n",
                encoding="utf-8",
            )

    def _checkpoint_path(self) -> Path:
        path = Path(self.config.test.checkpoint)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("test.checkpoint must be a relative path without '..'")
        return self.output_dir / path

    def _components(self):
        data_loader = build_data_loader(self.config.data, seed=self._data_seed())
        data_loader.setup()
        model = build_model(self.config.model)
        loss_fn = build_loss(self.config.train.loss)
        return data_loader, model, loss_fn

    def _data_seed(self) -> int:
        return self.config.experiment.seed if self.config.data.seed is None else self.config.data.seed

    def sanity(self) -> dict[str, Any]:
        if self.config.comparison is not None:
            from dl_research.experiment.comparison_runner import ComparisonRunner

            return ComparisonRunner(self).sanity()
        enforce_execution_policy(self.config, self.root)
        seed_everything(self.config.experiment.seed, self.config.experiment.deterministic)
        device = resolve_device(self.config.train.device)
        data_loader, model, loss_fn = self._components()
        model.to(device)
        inputs, targets = next(iter(data_loader.train_loader()))
        inputs = inputs.to(device)
        targets = targets.to(device)
        outputs = model(inputs)
        loss = loss_fn(outputs, targets)
        if not torch.isfinite(loss):
            raise FloatingPointError("non-finite sanity-check loss")
        loss.backward()
        gradients = [
            parameter.grad
            for parameter in model.parameters()
            if parameter.requires_grad and parameter.grad is not None
        ]
        if not gradients:
            raise RuntimeError("sanity check produced no gradients")
        if not all(torch.isfinite(gradient).all() for gradient in gradients):
            raise FloatingPointError("sanity check produced non-finite gradients")
        return {
            "experiment_id": self.config.experiment.id,
            "loss": float(loss.detach()),
            "input_shape": list(inputs.shape),
            "output_shape": list(outputs.shape),
            "gradient_tensors": len(gradients),
        }

    def train(self, *, write_artifact: bool = True) -> dict[str, Any]:
        if self.config.comparison is not None:
            raise ValueError("comparison training requires the complete cycle, not a single train call")
        enforce_execution_policy(self.config, self.root)
        seed_everything(self.config.experiment.seed, self.config.experiment.deterministic)
        self._prepare_output_dir()
        device = resolve_device(self.config.train.device)
        data_loader, model, loss_fn = self._components()
        optimizer = build_optimizer(model, self.config.train.optimizer)
        checkpoint = self._checkpoint_path()
        trainer = Trainer(
            model=model,
            optimizer=optimizer,
            loss_fn=loss_fn,
            device=device,
            config=self.config.train,
            checkpoint_path=checkpoint,
            checkpoint_metadata={
                "experiment_id": self.config.experiment.id,
                "config_sha256": config_sha256(self.config.source_path),
            },
        )
        result = trainer.fit(data_loader.train_loader(), data_loader.validation_loader())
        training = result.to_dict()
        training["checkpoint_path"] = relative_path(checkpoint, self.root)
        payload = {
            "experiment_id": self.config.experiment.id,
            "stage": self.config.experiment.stage,
            "training": training,
        }
        if write_artifact:
            atomic_write_json(self.output_dir / "train_metrics.json", payload)
        return payload

    def test(self, *, write_artifact: bool = True) -> dict[str, Any]:
        if self.config.comparison is not None:
            raise ValueError("comparison evaluation requires the complete cycle")
        enforce_execution_policy(self.config, self.root)
        seed_everything(self.config.experiment.seed, self.config.experiment.deterministic)
        self._prepare_output_dir()
        device = resolve_device(self.config.test.device)
        data_loader, model, loss_fn = self._components()
        checkpoint = self._checkpoint_path()
        if not checkpoint.is_file():
            raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
        payload = torch.load(checkpoint, map_location=device, weights_only=True)
        model.load_state_dict(payload["model_state"])
        tester = Tester(
            model=model,
            loss_fn=loss_fn,
            device=device,
            max_batches=self.config.test.max_batches,
        )
        result = tester.evaluate(data_loader.test_loader())
        output = {
            "experiment_id": self.config.experiment.id,
            "stage": self.config.experiment.stage,
            "test": result.to_dict(),
        }
        if write_artifact:
            atomic_write_json(self.output_dir / "test_metrics.json", output)
        return output

    def _metric_value(self, test_payload: dict[str, Any]) -> float:
        name = self.config.decision.primary_metric
        if name == "test_accuracy":
            return float(test_payload["test"]["accuracy"])
        if name == "test_loss":
            return float(test_payload["test"]["loss"])
        raise ValueError(f"unsupported primary metric: {name}")

    def _baseline_comparison(self, name: str, value: float) -> dict[str, Any] | None:
        baseline_id = self.config.experiment.baseline_id
        if baseline_id is None:
            return None
        metrics_path: Path | None = None
        index_path = self.root / "experiments/INDEX.json"
        if index_path.is_file():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            for item in index.get("experiments", []):
                if item.get("id") == baseline_id and isinstance(item.get("metrics"), str):
                    metrics_path = self.root / item["metrics"]
                    break
        if metrics_path is None:
            metrics_path = self.root / "artifacts/results" / baseline_id / "metrics.json"
        if not metrics_path.is_file():
            return {"baseline_id": baseline_id, "status": "missing"}
        baseline = json.loads(metrics_path.read_text(encoding="utf-8"))
        baseline_metric = baseline.get("primary_metric", {})
        if baseline_metric.get("name") != name:
            return {
                "baseline_id": baseline_id,
                "status": "incompatible_metric",
                "baseline_metric": baseline_metric.get("name"),
            }
        baseline_value = float(baseline_metric["value"])
        absolute_delta = value - baseline_value
        directional_effect = (
            absolute_delta
            if self.config.decision.direction == "maximize"
            else -absolute_delta
        )
        if directional_effect > 0:
            directional_signal = "favorable"
        elif directional_effect < 0:
            directional_signal = "adverse"
        else:
            directional_signal = "flat"
        meets_minimum_effect = None
        if self.config.decision.mode == "threshold":
            assert self.config.decision.minimum_effect is not None
            meets_minimum_effect = (
                directional_effect >= self.config.decision.minimum_effect
            )
        return {
            "baseline_id": baseline_id,
            "status": "available",
            "metric": name,
            "direction": self.config.decision.direction,
            "baseline_value": baseline_value,
            "current_value": value,
            "absolute_delta": absolute_delta,
            "directional_effect": directional_effect,
            "directional_signal": directional_signal,
            "decision_mode": self.config.decision.mode,
            "minimum_effect": self.config.decision.minimum_effect,
            "meets_minimum_effect": meets_minimum_effect,
            "relative_delta": None
            if baseline_value == 0
            else absolute_delta / abs(baseline_value),
        }

    def cycle(self) -> dict[str, Any]:
        """Run one training and test cycle and retain aggregate artifacts only."""
        if self.config.comparison is not None:
            from dl_research.experiment.comparison_runner import ComparisonRunner

            return ComparisonRunner(self).cycle()
        train_payload = self.train(write_artifact=False)
        test_payload = self.test(write_artifact=False)
        device = resolve_device(self.config.test.device)
        data_loader = build_data_loader(self.config.data, seed=self._data_seed())
        data_loader.setup()
        model = build_model(self.config.model)
        digest = config_sha256(self.config.source_path)
        primary_name = self.config.decision.primary_metric
        primary_value = self._metric_value(test_payload)
        metrics = {
            "schema_version": "2.0",
            "experiment_id": self.config.experiment.id,
            "stage": self.config.experiment.stage,
            "review_mode": self.config.experiment.review_mode,
            "status": "completed",
            "baseline_id": self.config.experiment.baseline_id,
            "queue_id": self.config.experiment.queue_id,
            "primary_metric": {
                "name": primary_name,
                "value": primary_value,
                "direction": self.config.decision.direction,
                "decision_mode": self.config.decision.mode,
                "minimum_effect": self.config.decision.minimum_effect,
            },
            "baseline_comparison": self._baseline_comparison(primary_name, primary_value),
            "training": train_payload["training"],
            "test": test_payload["test"],
            "config_sha256": digest,
            "artifacts": {"checkpoint": relative_path(self._checkpoint_path(), self.root)},
        }
        manifest = {
            "schema_version": "2.0",
            "experiment_id": self.config.experiment.id,
            "config": relative_path(self.config.source_path, self.root),
            "config_sha256": digest,
            "review_mode": self.config.experiment.review_mode,
            "environment": environment_manifest(self.root, device),
            "dataset": data_loader.metadata(),
            "model": {
                "name": self.config.model.name,
                "trainable_parameters": model.trainable_parameter_count(),
            },
        }
        self._prepare_output_dir()
        atomic_write_json(self.output_dir / "metrics.json", metrics)
        atomic_write_json(self.output_dir / "manifest.json", manifest)
        return metrics
