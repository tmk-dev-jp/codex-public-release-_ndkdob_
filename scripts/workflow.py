"""Deterministic experiment state-machine helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import atomic_write_json, read_json
from scripts.decision_integrity import require_decision_integrity

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"PLANNED"},
    "PLANNED": {"DRAFT", "IMPLEMENTED"},
    "IMPLEMENTED": {"SANITY_PASSED", "FAILED"},
    "SANITY_PASSED": {"TRAINED", "FAILED"},
    "TRAINED": {"REVIEW_REQUIRED", "READY_TO_FINALIZE", "FAILED"},
    "REVIEW_REQUIRED": {"READY_TO_FINALIZE", "FAILED"},
    "READY_TO_FINALIZE": {"FINALIZED", "FAILED"},
    "FAILED": {"IMPLEMENTED", "ABORTED"},
}


def state_path(root: Path) -> Path:
    return root / "research/STATE.json"


def active_dir(root: Path, experiment_id: str) -> Path:
    return root / "experiments/active" / experiment_id


def experiment_manifest_path(root: Path, experiment_id: str) -> Path:
    return active_dir(root, experiment_id) / "MANIFEST.json"


def comparison_results_recorded(root: Path, manifest: dict[str, Any]) -> bool:
    return (root / manifest["result_dir"] / "comparison_state.json").exists()


def require_active(
    root: Path, experiment_id: str, phases: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_decision_integrity(root, experiment_id)
    state = read_json(state_path(root))
    if state.get("active_experiment") != experiment_id:
        raise ValueError(f"active experiment is not {experiment_id}")
    manifest_path = experiment_manifest_path(root, experiment_id)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"experiment manifest not found: {experiment_id}")
    manifest = read_json(manifest_path)
    phase = state.get("phase")
    if manifest.get("phase") != phase:
        raise ValueError("state and experiment manifest phases differ")
    if phases is not None and phase not in phases:
        allowed = ", ".join(sorted(phases))
        raise ValueError(f"phase must be one of {allowed}; current phase is {phase}")
    return state, manifest


def set_phase(
    root: Path,
    experiment_id: str,
    target: str,
    *,
    objective: str,
    review_required: bool | None = None,
    allow_same: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state, manifest = require_active(root, experiment_id)
    current = str(state.get("phase"))
    if target == current and allow_same:
        return state, manifest
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid phase transition: {current} -> {target}")
    state["phase"] = target
    state["project_status"] = "active"
    if review_required is not None:
        state["review_required"] = review_required
    state["next_action"] = {
        "mode": target.lower(),
        "queue_id": manifest.get("queue_id"),
        "objective": objective,
    }
    manifest["phase"] = target
    atomic_write_json(state_path(root), state)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    return state, manifest


def mark_failed(root: Path, experiment_id: str, objective: str) -> None:
    state, manifest = require_active(root, experiment_id)
    current = str(state.get("phase"))
    if "FAILED" not in ALLOWED_TRANSITIONS.get(current, set()):
        return
    state["phase"] = "FAILED"
    state["project_status"] = "active"
    state["review_required"] = False
    state["next_action"] = {
        "mode": "debug_failure",
        "queue_id": manifest.get("queue_id"),
        "objective": objective,
    }
    manifest["phase"] = "FAILED"
    atomic_write_json(state_path(root), state)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
