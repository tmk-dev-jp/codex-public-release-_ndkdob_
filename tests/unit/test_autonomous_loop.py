from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_research_memory import _novelty

from scripts.next_agent_action import next_agent_action
from scripts.next_autonomous_step import next_autonomous_step
from scripts.next_unattended_loop_step import next_unattended_loop_step


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _state(root: Path, mode: str, *, active: str | None, phase: str | None) -> None:
    _write_json(
        root / "research/STATE.json",
        {
            "active_experiment": active,
            "phase": phase,
            "next_action": {"mode": mode, "objective": "test route"},
        },
    )


def _cleared_novelty(root: Path, experiment_id: str) -> None:
    path = root / "research/novelty/NOVELTY_CHECKS.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _novelty(experiment_id)
        )
        + "\n",
        encoding="utf-8",
    )


def test_implemented_routes_to_runner(tmp_path: Path) -> None:
    _state(tmp_path, "implemented", active="EXP-TEST", phase="IMPLEMENTED")
    result = next_autonomous_step(tmp_path)
    assert "skill=$run-experiment" in result
    assert "operation=execution" in result


def test_implementation_review_routes_to_auditor(tmp_path: Path) -> None:
    _state(tmp_path, "review_implementation", active="EXP-TEST", phase="IMPLEMENTED")
    result = next_autonomous_step(tmp_path)
    assert "skill=$audit-experiment-implementation" in result
    assert "operation=implementation_review" in result


def test_locked_plan_routes_to_metric_gaming_audit(tmp_path: Path) -> None:
    _state(
        tmp_path,
        "audit_experiment_plan",
        active="EXP-TEST",
        phase="PLANNED",
    )
    _cleared_novelty(tmp_path, "EXP-TEST")
    result = next_autonomous_step(tmp_path)
    assert "skill=$audit-experiment-plan" in result
    assert "operation=planning" in result


@pytest.mark.parametrize("unattended", [False, True])
def test_missing_novelty_is_prepared_then_plan_audit_resumes(
    tmp_path: Path, unattended: bool
) -> None:
    _state(tmp_path, "audit_experiment_plan", active="EXP-TEST", phase="PLANNED")

    def route():
        if unattended:
            return next_unattended_loop_step(tmp_path, explicit_user_request=True)
        return next_autonomous_step(tmp_path)

    first = route()
    assert first.startswith("ready ")
    assert "skill=$audit-novelty" in first
    _cleared_novelty(tmp_path, "EXP-TEST")
    second = route()
    assert second.startswith("ready ")
    assert "skill=$audit-experiment-plan" in second
    state = json.loads((tmp_path / "research/STATE.json").read_text())
    assert state["phase"] == "PLANNED"
    assert state["next_action"]["mode"] == "audit_experiment_plan"


@pytest.mark.parametrize("unattended", [False, True])
@pytest.mark.parametrize("change,reason", [
    ({"risk": "high"}, "novelty-risk-high"),
    ({"human_review_needed": True}, "novelty-human-review-needed"),
    ({"similar_items": []}, "novelty-evidence-incomplete"),
    ({"decision": "reject"}, "novelty-not-cleared"),
])
def test_substantive_novelty_stops_are_not_preparation(
    tmp_path: Path, unattended: bool, change: dict, reason: str,
) -> None:
    _state(tmp_path, "audit_experiment_plan", active="EXP-TEST", phase="PLANNED")
    _cleared_novelty(tmp_path, "EXP-TEST")
    path = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    record = _novelty("EXP-TEST")
    record.update(change)
    path.write_text(json.dumps(record) + "\n")
    result = (
        next_unattended_loop_step(tmp_path, explicit_user_request=True)
        if unattended else next_autonomous_step(tmp_path)
    )
    assert result.startswith("blocked ") and f"reason={reason}" in result


@pytest.mark.parametrize("mode,phase", [
    ("implemented", "IMPLEMENTED"), ("sanity_passed", "SANITY_PASSED"),
])
@pytest.mark.parametrize("approved_id", [None, "EXP-OTHER", "EXP-TEST"])
def test_ordinary_full_approval_is_checked_before_execution(
    tmp_path: Path, mode: str, phase: str, approved_id: str | None,
) -> None:
    _state(tmp_path, mode, active="EXP-TEST", phase=phase)
    path = tmp_path / "research/STATE.json"
    state = json.loads(path.read_text())
    state.update(stage="full", approvals={"full_training_experiment_id": approved_id})
    _write_json(path, state)
    result = next_autonomous_step(tmp_path)
    if approved_id == "EXP-TEST":
        assert result.startswith("ready ")
    else:
        assert result.startswith("blocked ") and "reason=full-approval-required" in result


def test_trained_recovery_routes_to_runner(tmp_path: Path) -> None:
    _state(tmp_path, "trained", active="EXP-TEST", phase="TRAINED")
    result = next_autonomous_step(tmp_path)
    assert "skill=$run-experiment" in result


def test_review_routes_to_integrity_before_evaluation(tmp_path: Path) -> None:
    _state(tmp_path, "review_required", active="EXP-TEST", phase="REVIEW_REQUIRED")
    _write_json(
        tmp_path / "experiments/active/EXP-TEST/MANIFEST.json",
        {"integrity_audit": None},
    )
    result = next_autonomous_step(tmp_path)
    assert "skill=$audit-experiment-integrity" in result
    assert "operation=result_review" in result


def test_review_with_verdict_only_routes_back_to_integrity(tmp_path: Path) -> None:
    _state(tmp_path, "review_required", active="EXP-TEST", phase="REVIEW_REQUIRED")
    _write_json(
        tmp_path / "experiments/active/EXP-TEST/MANIFEST.json",
        {"integrity_audit": {"verdict": "warn"}},
    )
    result = next_autonomous_step(tmp_path)
    assert "skill=$audit-experiment-integrity" in result
    assert "operation=result_review" in result


def test_post_finalize_selection_routes_to_creator(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment", active=None, phase=None)
    result = next_autonomous_step(tmp_path)
    assert "skill=$select-next-experiment" in result
    assert "operation=post_result" in result


@pytest.mark.parametrize("mode", ["maintain_memory", "update_direction", "select_experiment"])
def test_post_result_routes_reject_an_active_experiment(tmp_path: Path, mode: str) -> None:
    _state(tmp_path, mode, active="EXP-TEST", phase="DRAFT")
    result = next_autonomous_step(tmp_path)
    assert result.startswith("blocked ")
    assert "reason=unexpected-active-experiment" in result
    assert "operation=post_result" in result


def test_operation_groups_only_bounded_machine_followups(tmp_path: Path) -> None:
    cases = {
        "maintain_memory": "post_result",
        "update_direction": "post_result",
        "select_experiment": "post_result",
    }
    for mode, operation in cases.items():
        _state(tmp_path, mode, active=None, phase=None)
        result = next_autonomous_step(tmp_path)
        assert result.startswith("ready ")
        assert "max_phases=3" in result
        assert f"operation={operation}" in result


def test_agent_phase_without_active_experiment_is_blocked(tmp_path: Path) -> None:
    _state(tmp_path, "plan_experiment", active=None, phase="DRAFT")

    result = next_autonomous_step(tmp_path)

    assert result.startswith("blocked ")
    assert "reason=no-active-experiment" in result


def test_plan_review_remains_a_human_gate(tmp_path: Path) -> None:
    _state(tmp_path, "review_experiment_plan", active=None, phase="PLANNED")
    result = next_autonomous_step(tmp_path)
    assert result.startswith("blocked ")
    assert "operation=human_plan_review" in result


@pytest.mark.parametrize("progress", ["failed", "running", "completed", "invalid-json"])
def test_recorded_comparison_blocks_repair_before_reading_code(tmp_path, progress):
    _state(tmp_path, "debug_failure", active="EXP-TEST", phase="FAILED")
    manifest = tmp_path / "experiments/active/EXP-TEST/MANIFEST.json"
    _write_json(manifest, {"phase": "FAILED", "result_dir": "artifacts/results/EXP-TEST"})
    marker = tmp_path / "artifacts/results/EXP-TEST/comparison_state.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        progress if progress == "invalid-json" else json.dumps({"status": progress}),
        encoding="utf-8",
    )
    paths = [tmp_path / "research/STATE.json", manifest, marker]
    before = [path.read_bytes() for path in paths]

    action = next_agent_action(tmp_path, "repair", "EXP-TEST")
    assert action == "action=blocked reason=recorded-comparison-requires-human-disposition"
    result = next_autonomous_step(tmp_path)
    assert result.startswith("blocked ")
    assert "reason=recorded-comparison-requires-human-disposition" in result
    assert "prompt=" not in result
    assert [path.read_bytes() for path in paths] == before


@pytest.mark.parametrize("comparison", [False, True])
def test_unrecorded_failure_allows_scoped_repair(tmp_path, comparison):
    from test_repair_context import EXPERIMENT_ID, _failed_root

    _failed_root(tmp_path, comparison=comparison)
    assert next_agent_action(tmp_path, "repair", EXPERIMENT_ID).startswith("action=build ")
    result = next_autonomous_step(tmp_path)
    assert result.startswith("ready ")
    assert "operation=repair" in result


def test_missing_failure_manifest_blocks_repair(tmp_path):
    _state(tmp_path, "debug_failure", active="EXP-TEST", phase="FAILED")
    result = next_autonomous_step(tmp_path)
    assert result.startswith("blocked ")
    assert "agent-preflight-FileNotFoundError" in result


def test_repair_gate_requires_failed_phase(tmp_path):
    _state(tmp_path, "debug_failure", active="EXP-TEST", phase="TRAINED")
    _write_json(
        tmp_path / "experiments/active/EXP-TEST/MANIFEST.json",
        {"phase": "TRAINED", "result_dir": "artifacts/results/EXP-TEST"},
    )
    with pytest.raises(ValueError, match="phase must be one of FAILED"):
        next_agent_action(tmp_path, "repair", "EXP-TEST")
