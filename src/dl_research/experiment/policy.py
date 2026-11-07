"""Compute-budget and approval gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dl_research.config import ExperimentConfig
from dl_research.exceptions import PolicyError


def _limit(value: int | None, maximum: int, name: str) -> None:
    if value is None or value > maximum:
        raise PolicyError(f"{name} must be set and <= {maximum} for this stage")


def enforce_execution_policy(config: ExperimentConfig, root: Path) -> dict[str, Any]:
    state_path = root / "research/STATE.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PolicyError("research/STATE.json is missing or invalid") from exc

    policies = state.get("execution_policy", {})
    stage = config.experiment.stage
    policy = policies.get(stage)
    if not isinstance(policy, dict):
        raise PolicyError(f"execution policy is missing for stage {stage}")

    if stage in {"smoke", "pilot"}:
        max_epochs = int(policy["max_epochs"])
        if config.train.epochs > max_epochs:
            raise PolicyError(f"train.epochs exceeds {stage} limit {max_epochs}")
        _limit(
            config.train.max_train_batches,
            int(policy["max_train_batches"]),
            "train.max_train_batches",
        )
        _limit(
            config.train.max_validation_batches,
            int(policy["max_validation_batches"]),
            "train.max_validation_batches",
        )
        _limit(config.test.max_batches, int(policy["max_test_batches"]), "test.max_batches")
    elif stage == "full" and policy.get("requires_explicit_approval", True):
        approved = state.get("approvals", {}).get("full_training_experiment_id")
        if approved != config.experiment.id:
            raise PolicyError(
                "full training requires matching approvals.full_training_experiment_id"
            )
    return policy
