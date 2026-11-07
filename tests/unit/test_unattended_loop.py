from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_research_memory import _novelty

import scripts.approve_plan as approve_plan_module
import scripts.next_unattended_loop_step as unattended_module
from scripts.next_autonomous_step import MODE_TO_SKILL
from scripts.next_unattended_loop_step import next_unattended_loop_step


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _state(
    root: Path,
    mode: str,
    *,
    active: str | None = None,
    latest: str | None = None,
    phase: str | None = None,
    stage: str | None = None,
    approvals: dict[str, object] | None = None,
    unattended: dict[str, object] | None = None,
) -> None:
    _write_json(
        root / "research/STATE.json",
        {
            "active_experiment": active,
            "latest_completed_experiment": latest,
            "phase": phase,
            "stage": stage,
            "approvals": approvals or {},
            "unattended_loop": unattended
            or {
                "status": "idle",
                "target_experiment": None,
                "last_mode": None,
            },
            "next_action": {"mode": mode, "objective": "test route"},
        },
    )


def test_router_requires_explicit_current_request(tmp_path: Path) -> None:
    assert next_unattended_loop_step(tmp_path) == (
        "blocked reason=explicit-user-request-required"
    )


def test_preflight_error_names_the_fix_without_changing_phase_or_target(tmp_path, monkeypatch):
    _state(tmp_path, "plan_experiment", active="EXP-001", phase="DRAFT", stage="smoke")

    def rejected_presentation(*args, **kwargs):
        raise ValueError("missing field: Evaluation\ncorrect the existing record")

    monkeypatch.setattr(unattended_module, "next_agent_action", rejected_presentation)
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "detail=missing field: Evaluation correct the existing record" in result
    assert "\n" not in result
    state = json.loads((tmp_path / "research/STATE.json").read_text(encoding="utf-8"))
    assert state["phase"] == "DRAFT"
    assert state["active_experiment"] == "EXP-001"
    assert state["unattended_loop"]["target_experiment"] == "EXP-001"


def test_fresh_loop_selects_one_target(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment", latest="EXP-OLD")
    _queue(tmp_path)
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert result.startswith("ready ")
    assert "target=pending" in result
    assert "skill=$select-next-experiment" in result


def _queue(root: Path, **changes: object) -> None:
    item = {
        "id": "Q-NEW",
        "status": "ready",
        "hypothesis": "The method improves accuracy under shift",
        "falsifier": "No improvement over baseline",
        "minimal_test": "Paired pilot comparison with essential controls",
        "primary_metric": "accuracy",
        **changes,
    }
    _write_json(root / "research/QUEUE.json", {"items": [item]})


def test_exhausted_queue_replenishes_once_then_blocks(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment")
    _write_json(tmp_path / "research/QUEUE.json", {"items": []})
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=replenish-hypotheses" in result
    assert "skill=$replenish-research-hypotheses" in result
    state = json.loads((tmp_path / "research/STATE.json").read_text())
    assert state["active_experiment"] is None
    assert state["next_action"]["mode"] == "select_experiment"
    assert state["unattended_loop"]["target_experiment"] is None
    assert next_unattended_loop_step(tmp_path, explicit_user_request=True) == (
        "blocked mode=select_experiment reason=no-viable-hypothesis"
    )


def test_replenished_queue_returns_to_target_creation(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment")
    _write_json(tmp_path / "research/QUEUE.json", {"items": []})
    next_unattended_loop_step(tmp_path, explicit_user_request=True)
    _queue(tmp_path)
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=create-target" in result
    assert "target=pending" in result
    assert next_unattended_loop_step(tmp_path) == (
        "blocked reason=explicit-user-request-required"
    )


def test_unusable_queue_entries_trigger_investigation(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment")
    for changes in (
        {"status": "completed"}, {"status": "rejected"}, {"status": "deferred"},
        {"status": "stop"}, {"forbidden_by_policy": True},
        {"hypothesis": "<falsifiable hypothesis>"}, {"falsifier": ""},
    ):
        _queue(tmp_path, **changes)
        assert not unattended_module.has_ready_hypothesis(tmp_path)


def test_ready_legacy_draft_and_mathematical_inequality_are_selectable(tmp_path: Path) -> None:
    _queue(tmp_path, status="draft", hypothesis="The method gives error < 0.1")
    assert unattended_module.has_ready_hypothesis(tmp_path)


def test_persisted_target_is_reused_with_a_new_explicit_request(tmp_path: Path) -> None:
    _state(
        tmp_path,
        "plan_experiment",
        active="EXP-001",
        phase="DRAFT",
        stage="smoke",
        unattended={
            "status": "in_progress",
            "target_experiment": "EXP-001",
            "last_mode": "select_experiment",
        },
    )
    original = unattended_module.next_agent_action
    unattended_module.next_agent_action = (
        lambda *args, **kwargs: "action=delegate agent=research_planner"
    )
    try:
        result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    finally:
        unattended_module.next_agent_action = original
    assert "target=EXP-001" in result
    assert "skill=$plan-experiment" in result
    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    assert state["unattended_loop"]["last_mode"] == "plan_experiment"


def test_persisted_target_does_not_persist_authorization(tmp_path: Path) -> None:
    _state(
        tmp_path,
        "plan_experiment",
        active="EXP-001",
        phase="DRAFT",
        unattended={
            "status": "in_progress",
            "target_experiment": "EXP-001",
            "last_mode": "select_experiment",
        },
    )
    assert next_unattended_loop_step(tmp_path) == (
        "blocked reason=explicit-user-request-required"
    )


def test_completed_target_stops_before_selecting_another(tmp_path: Path) -> None:
    _state(tmp_path, "select_experiment", latest="EXP-001")
    result = next_unattended_loop_step(
        tmp_path,
        target_id="EXP-001",
        explicit_user_request=True,
    )
    assert result == "complete target=EXP-001 next=select_experiment"
    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    assert state["unattended_loop"]["status"] == "idle"
    assert state["unattended_loop"]["target_experiment"] is None


@pytest.mark.parametrize("stage", ["smoke", "full"])
def test_plan_gate_routes_to_traceable_advance_approval(tmp_path: Path, stage: str) -> None:
    _state(
        tmp_path,
        "review_experiment_plan",
        active="EXP-001",
        phase="PLANNED",
        stage=stage,
    )
    novelty = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    novelty.parent.mkdir(parents=True, exist_ok=True)
    novelty.write_text(
        json.dumps(
            _novelty("EXP-001")
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "experiments/active/EXP-001/MANIFEST.json",
        {"phase": "PLANNED"},
    )
    original = unattended_module.require_accepted_plan_audit
    unattended_module.require_accepted_plan_audit = lambda *args, **kwargs: None
    try:
        result = next_unattended_loop_step(
            tmp_path,
            target_id="EXP-001",
            explicit_user_request=True,
        )
    finally:
        unattended_module.require_accepted_plan_audit = original
    assert "action=approve-plan" in result
    assert "source=explicit_unattended_loop" in result


def test_plan_warn_blocks_unattended_approval(tmp_path: Path) -> None:
    _state(
        tmp_path,
        "review_experiment_plan",
        active="EXP-001",
        phase="PLANNED",
        stage="smoke",
    )
    novelty = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    novelty.parent.mkdir(parents=True, exist_ok=True)
    novelty.write_text(
        json.dumps(
            _novelty("EXP-001")
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "experiments/active/EXP-001/MANIFEST.json",
        {"phase": "PLANNED", "plan_audit": {"verdict": "warn"}},
    )

    result = next_unattended_loop_step(
        tmp_path,
        target_id="EXP-001",
        explicit_user_request=True,
    )

    assert result.endswith("reason=plan-audit-pass-required")


def test_implementation_rechecks_novelty_gate(tmp_path: Path) -> None:
    _state(
        tmp_path,
        "implement_experiment",
        active="EXP-001",
        phase="PLANNED",
        stage="smoke",
    )
    novelty = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    novelty.parent.mkdir(parents=True, exist_ok=True)
    novelty.write_text(
        json.dumps(
            {
                "experiment_id": "EXP-001",
                "risk": "high",
                "decision": "proceed",
                "human_review_needed": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = next_unattended_loop_step(
        tmp_path,
        target_id="EXP-001",
        explicit_user_request=True,
    )
    assert result.endswith("reason=novelty-risk-high")


def test_full_stage_can_plan_before_separate_approval(tmp_path: Path, monkeypatch) -> None:
    _state(tmp_path, "plan_experiment", active="EXP-001", phase="DRAFT", stage="full")
    monkeypatch.setattr(
        unattended_module, "next_agent_action",
        lambda *args, **kwargs: "action=delegate agent=research_planner",
    )
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=run-phase skill=$plan-experiment" in result


@pytest.mark.parametrize("mode,phase", [
    ("implemented", "IMPLEMENTED"),
    ("sanity_passed", "SANITY_PASSED"),
])
@pytest.mark.parametrize("approved_id", [None, "EXP-OTHER"])
def test_full_stage_still_requires_separate_approval(
    tmp_path: Path, mode: str, phase: str, approved_id: str | None,
) -> None:
    _state(
        tmp_path,
        mode,
        active="EXP-001",
        phase=phase,
        stage="full",
        approvals={"full_training_experiment_id": approved_id},
    )
    result = next_unattended_loop_step(
        tmp_path,
        target_id="EXP-001",
        explicit_user_request=True,
    )
    assert result.endswith("reason=full-approval-required")


@pytest.mark.parametrize("mode,phase,skill", [
    ("implement_experiment", "PLANNED", "$implement-experiment"),
    ("review_implementation", "IMPLEMENTED", "$audit-experiment-implementation"),
    ("trained", "TRAINED", "$run-experiment"),
    ("ready_to_finalize", "READY_TO_FINALIZE", "$evaluate-experiment"),
])
def test_full_nonexecution_work_does_not_require_compute_approval(
    tmp_path: Path, monkeypatch, mode: str, phase: str, skill: str,
) -> None:
    from test_autonomous_loop import _cleared_novelty

    _state(tmp_path, mode, active="EXP-001", phase=phase, stage="full")
    _cleared_novelty(tmp_path, "EXP-001")
    monkeypatch.setattr(
        unattended_module, "next_agent_action",
        lambda *args, **kwargs: "action=delegate agent=experiment_implementer",
    )
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert result.startswith("ready ") and f"skill={skill}" in result


def test_full_execution_routes_after_matching_approval(tmp_path: Path) -> None:
    _state(
        tmp_path, "implemented", active="EXP-001", phase="IMPLEMENTED", stage="full",
        approvals={"full_training_experiment_id": "EXP-001"},
    )
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=run-phase skill=$run-experiment" in result


def test_skill_is_not_reachable_from_normal_autonomy() -> None:
    root = Path(__file__).resolve().parents[2]
    assert "$run-one-unattended-loop" not in MODE_TO_SKILL.values()
    policy = (
        root / ".agents/skills/run-one-unattended-loop/agents/openai.yaml"
    ).read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in policy
    for relative in (
        "automation/ONE_CYCLE_PROMPT.md",
        "automation/AUTONOMOUS_LOOP_PROMPT.md",
    ):
        assert "$run-one-unattended-loop" not in (root / relative).read_text(
            encoding="utf-8"
        )


def test_unattended_plan_approval_records_its_source(tmp_path: Path) -> None:
    experiment_id = "EXP-001"
    _state(
        tmp_path,
        "review_experiment_plan",
        active=experiment_id,
        phase="PLANNED",
        stage="smoke",
    )
    manifest_path = tmp_path / "experiments/active" / experiment_id / "MANIFEST.json"
    _write_json(
        manifest_path,
        {"experiment_id": experiment_id, "phase": "PLANNED", "queue_id": "Q-001"},
    )

    original_build_context = approve_plan_module.build_context
    original_plan_audit = approve_plan_module.require_accepted_plan_audit
    approve_plan_module.build_context = lambda root: root / "research/CONTEXT.md"
    approve_plan_module.require_accepted_plan_audit = lambda *args, **kwargs: None
    try:
        approve_plan_module.approve_plan(
            tmp_path,
            experiment_id,
            "explicit_unattended_loop",
        )
    finally:
        approve_plan_module.build_context = original_build_context
        approve_plan_module.require_accepted_plan_audit = original_plan_audit

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["plan_review"] == {
        "status": "approved",
        "source": "explicit_unattended_loop",
    }


def test_completed_saved_target_does_not_block_new_active(
    tmp_path: Path,
) -> None:
    _state(
        tmp_path,
        "plan_experiment",
        active="EXP-002",
        latest="EXP-001",
        phase="DRAFT",
        stage="smoke",
        unattended={
            "status": "in_progress",
            "target_experiment": "EXP-001",
            "last_mode": "update_direction",
        },
    )

    original = unattended_module.next_agent_action
    unattended_module.next_agent_action = (
        lambda *args, **kwargs: "action=delegate agent=research_planner"
    )
    try:
        result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    finally:
        unattended_module.next_agent_action = original

    assert "target=EXP-002" in result
    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    assert state["unattended_loop"]["status"] == "in_progress"
    assert state["unattended_loop"]["target_experiment"] == "EXP-002"
