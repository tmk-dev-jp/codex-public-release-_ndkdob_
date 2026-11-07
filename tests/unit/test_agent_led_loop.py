from __future__ import annotations

from pathlib import Path

import pytest
from test_plan_audit import EXPERIMENT_ID, _accept, _root
from test_research_memory import _novelty

from scripts.approve_plan import approve_plan
from scripts.common import atomic_write_json, read_json
from scripts.next_agent_led_loop_step import next_agent_led_loop_step
from scripts.next_unattended_loop_step import next_unattended_loop_step
from scripts.research_decision import (
    accept_decision,
    bind_worker,
    decision_action,
    dispatch_decision,
    prepare_decision,
)
from scripts.research_memory import append_jsonl, latest_novelty


def _setup(root: Path, verdict: str | None = "warn") -> Path:
    active = _root(root)
    append_jsonl(root / "research/novelty/NOVELTY_CHECKS.jsonl", _novelty(EXPERIMENT_ID))
    atomic_write_json(root / "experiments/INDEX.json", {"experiments": []})
    if verdict:
        _accept(root, verdict)
    state = read_json(root / "research/STATE.json")
    state["agent_led_loop"] = {
        "status": "in_progress", "target_experiment": EXPERIMENT_ID, "last_mode": "planning",
    }
    atomic_write_json(root / "research/STATE.json", state)
    return active


def _assessment(refs: list[str]) -> dict:
    return {
        "observations": [
            {"source": ref, "observation": "The fixture preserves its bounded comparison."}
            for ref in refs
        ],
        "counterargument": "Readiness evidence does not establish research utility.",
        "uncertainty": "Representative pilot outcomes remain unobserved.",
        "change_condition": "Revise if required matched controls cannot be implemented.",
        "audit_response": "Keep the diagnostic-only guardrail and readiness-only scope.",
    }


def _respond(root: Path, issue: str, action: str, **extra) -> Path:
    request = prepare_decision(root, EXPERIMENT_ID, issue)
    assert decision_action(
        root, EXPERIMENT_ID, issue, explicit_user_request=True,
    ).startswith("action=delegate ")
    dispatch_decision(root, EXPERIMENT_ID, issue)
    bind_worker(root, EXPERIMENT_ID, issue, worker_id="fixture-worker")
    refs = ["research/GOAL.md"]
    if issue == "plan" and action == "approve":
        refs = [f"experiments/active/{EXPERIMENT_ID}/{name}"
                for name in ("EXPERIMENT.md", "PLAN_AUDIT.md")]
    atomic_write_json(request.parent / "RESPONSE.json", {
        "action": action, "rationale": "The recorded evidence supports this scoped decision.",
        "evidence_refs": refs, "assessment": _assessment(refs), **extra,
    })
    return request.parent


def test_authorization_is_required_even_with_stored_target(tmp_path):
    _setup(tmp_path)
    before = (tmp_path / "research/STATE.json").read_bytes()
    assert "explicit-agent-led-request-required" in next_agent_led_loop_step(tmp_path)
    assert "explicit-agent-led-request-required" in decision_action(tmp_path, EXPERIMENT_ID, "plan")
    assert (tmp_path / "research/STATE.json").read_bytes() == before


@pytest.mark.parametrize("verdict", ["pass", "warn"])
def test_scientist_can_approve_current_pass_or_warn_without_changing_audit(tmp_path, verdict):
    active = _setup(tmp_path, verdict)
    before = (active / "PLAN_AUDIT.md").read_bytes()
    route = next_agent_led_loop_step(tmp_path, explicit_user_request=True)
    assert "issue=plan" in route and "action=build" in route
    _respond(tmp_path, "plan", "approve")
    accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    state = read_json(tmp_path / "research/STATE.json")
    manifest = read_json(active / "MANIFEST.json")
    assert state["next_action"]["mode"] == "implement_experiment"
    assert manifest["plan_review"]["source"] == "agent_research_decision"
    assert manifest["plan_review"]["decision_sha256"]
    assert manifest["plan_audit"]["verdict"] == verdict
    assert (active / "PLAN_AUDIT.md").read_bytes() == before


def test_old_loop_still_blocks_warn_and_keeps_separate_control(tmp_path):
    _setup(tmp_path)
    assert "plan-audit-pass-required" in next_unattended_loop_step(
        tmp_path, explicit_user_request=True,
    )
    old_control = read_json(tmp_path / "research/STATE.json")["unattended_loop"]
    assert "issue=plan" in next_agent_led_loop_step(tmp_path, explicit_user_request=True)
    assert read_json(tmp_path / "research/STATE.json")["unattended_loop"] == old_control


def test_fail_cannot_be_approved_but_can_return_to_draft(tmp_path):
    rejected = tmp_path / "rejected"
    _setup(rejected, "fail")
    _respond(rejected, "plan", "approve")
    with pytest.raises(ValueError, match="pass or warn"):
        accept_decision(rejected, EXPERIMENT_ID, "plan")
    active = _setup(tmp_path, "fail")
    _respond(tmp_path, "plan", "revise", instructions="Add the missing matched reference control.")
    accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    state = read_json(tmp_path / "research/STATE.json")
    assert state["phase"] == "DRAFT"
    assert state["next_action"]["mode"] == "revise_experiment_plan"
    assert read_json(active / "MANIFEST.json")["plan_audit"] is None
    assert (active / "RESEARCH_GUIDANCE.md").read_text().startswith("Add the missing")


def test_source_label_alone_cannot_approve_a_plan(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ValueError, match="current dispatched"):
        approve_plan(tmp_path, EXPERIMENT_ID, "agent_research_decision")


def test_changed_goal_cannot_reuse_a_prior_decision(tmp_path):
    active = _setup(tmp_path)
    _respond(tmp_path, "plan", "approve")
    (tmp_path / "research/GOAL.md").write_text("# Different research question\n")
    with pytest.raises((ValueError, FileNotFoundError)):
        accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert read_json(active / "MANIFEST.json").get("plan_review") is None


def test_dispatch_prevents_duplicate_worker_and_saved_response_is_reused(tmp_path):
    _setup(tmp_path)
    request = prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert "worker-pending-or-unavailable" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )
    with pytest.raises(ValueError, match="not permitted"):
        dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    atomic_write_json(request.parent / "RESPONSE.json", {"action": "stop"})
    assert "action=accept" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )
    with pytest.raises(ValueError):
        accept_decision(tmp_path, EXPERIMENT_ID, "plan")


@pytest.mark.parametrize("worker_id", ["worker-17", "/root/decision_trial"])
def test_bound_worker_can_be_inspected_but_not_replaced(tmp_path, worker_id):
    _setup(tmp_path)
    request = prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    path = bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id=worker_id)
    before = path.read_bytes()
    assert bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id=worker_id) == path
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="cannot replace"):
        bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id="worker-18")
    route = next_agent_led_loop_step(tmp_path, explicit_user_request=True)
    assert f"action=check-worker worker_id={worker_id}" in route
    assert f"request={request.relative_to(tmp_path)}" in route
    assert "action=delegate" not in route
    changed_question = decision_action(
        tmp_path, EXPERIMENT_ID, "plan", question="Another choice", explicit_user_request=True,
    )
    assert f"action=check-worker worker_id={worker_id}" in changed_question
    assert "another-decision-worker-pending" in changed_question
    # A real response takes precedence over the stored identity.
    atomic_write_json(request.parent / "RESPONSE.json", {"action": "stop"})
    assert "action=accept" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )


def test_worker_binding_requires_current_dispatched_request(tmp_path):
    _setup(tmp_path)
    request = prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    with pytest.raises(FileNotFoundError):
        bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id="worker-17")
    dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    before = (request.parent / "DISPATCHED.json").read_bytes()
    with pytest.raises(ValueError, match="invalid decision worker"):
        bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id="worker\nforged=live")
    snapshot = read_json(request)
    snapshot["question"] = "Changed after dispatch"
    atomic_write_json(request, snapshot)
    with pytest.raises(ValueError, match="changed after dispatch"):
        bind_worker(tmp_path, EXPERIMENT_ID, "plan", worker_id="worker-17")
    assert (request.parent / "DISPATCHED.json").read_bytes() == before


def test_valid_response_without_bound_worker_cannot_change_state(tmp_path):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    dispatch = read_json(folder / "DISPATCHED.json")
    dispatch.pop("worker_id")
    atomic_write_json(folder / "DISPATCHED.json", dispatch)
    state_before = (tmp_path / "research/STATE.json").read_bytes()
    manifest_before = (active / "MANIFEST.json").read_bytes()
    with pytest.raises(ValueError, match="bound worker ID"):
        accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert (tmp_path / "research/STATE.json").read_bytes() == state_before
    assert (active / "MANIFEST.json").read_bytes() == manifest_before
    assert not (folder / "ACCEPTED.json").exists()
    assert not (folder / "APPLYING.json").exists()


@pytest.mark.parametrize("has_response", [False, True])
@pytest.mark.parametrize("dispatched", [False, True])
def test_legacy_pending_requests_do_not_silently_dispatch_replacements(
    tmp_path, has_response, dispatched,
):
    _setup(tmp_path)
    request = prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    if dispatched:
        dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    snapshot = read_json(request)
    snapshot["schema_version"] = "1.0"
    atomic_write_json(request, snapshot)
    if has_response:
        atomic_write_json(request.parent / "RESPONSE.json", {"action": "stop"})
    assert "legacy-decision-request-requires-review" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )


def test_request_excludes_prior_conclusions_without_losing_locked_plan(tmp_path):
    from scripts.records import replace_section

    active = _setup(tmp_path)
    record = active / "EXPERIMENT.md"
    record.write_text(replace_section(
        record.read_text(), "## Conclusion", "EARLIER_AGENT_APPROVES",
    ))
    request = prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    snapshot = read_json(request)
    projection = snapshot["sources"][f"experiments/active/{EXPERIMENT_ID}/EXPERIMENT.md"]
    assert "EARLIER_AGENT_APPROVES" not in projection
    assert "## Conclusion" not in projection
    assert "Minimum discriminating evidence" in projection
    assert f"experiments/active/{EXPERIMENT_ID}/PLAN_AUDIT.md" in snapshot["sources"]
    dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    record.write_text(replace_section(record.read_text(), "## Conclusion", "EARLIER_AGENT_REJECTS"))
    assert "worker-pending-or-unavailable" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )
    assert request.read_text().find("EARLIER_AGENT_") == -1


@pytest.mark.parametrize("defect", [
    "missing", "counterargument", "uncertainty", "change_condition", "audit_response",
    "foreign_source", "missing_observation", "goal_only", "duplicate_source", "empty_observation",
])
def test_incomplete_or_untraceable_assessment_cannot_approve(tmp_path, defect):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    response = read_json(folder / "RESPONSE.json")
    if defect == "missing":
        response.pop("assessment")
    elif defect in {"counterargument", "uncertainty", "change_condition", "audit_response"}:
        response["assessment"][defect] = "pending"
    elif defect == "foreign_source":
        response["assessment"]["observations"][0]["source"] = "experiments/completed/unread.md"
    elif defect == "missing_observation":
        response["assessment"]["observations"].pop()
    elif defect == "goal_only":
        response["evidence_refs"] = ["research/GOAL.md"]
        response["assessment"] = _assessment(response["evidence_refs"])
    elif defect == "duplicate_source":
        response["evidence_refs"].append(response["evidence_refs"][0])
    else:
        response["assessment"]["observations"][0]["observation"] = ""
    atomic_write_json(folder / "RESPONSE.json", response)
    paths = [tmp_path / "research/STATE.json", active / "MANIFEST.json", active / "PLAN_AUDIT.md"]
    before = [path.read_bytes() for path in paths]
    with pytest.raises(ValueError):
        accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert [path.read_bytes() for path in paths] == before
    assert not (folder / "ACCEPTED.json").exists()
    assert not (folder / "APPLYING.json").exists()


@pytest.mark.parametrize("ref", ["https://", "https://bad host/paper", "https://user:pass@host/paper"])
def test_novelty_rejects_malformed_or_credentialed_external_references(tmp_path, ref):
    _setup(tmp_path)
    folder = _respond(
        tmp_path, "novelty", "stop", evidence_refs=[ref], assessment=_assessment([ref]),
    )
    with pytest.raises(ValueError, match="supplied evidence"):
        accept_decision(tmp_path, EXPERIMENT_ID, "novelty")
    assert not (folder / "ACCEPTED.json").exists()
    assert not (folder / "APPLYING.json").exists()


def test_novelty_human_judgment_is_resolved_with_evidence_then_reaudited(tmp_path):
    _setup(tmp_path)
    pending = _novelty(EXPERIMENT_ID)
    pending.update(decision="needs_human", human_review_needed=True)
    append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", pending)
    assert "issue=novelty" in next_agent_led_loop_step(tmp_path, explicit_user_request=True)
    _respond(tmp_path, "novelty", "record_novelty", novelty=_novelty(EXPERIMENT_ID))
    accept_decision(tmp_path, EXPERIMENT_ID, "novelty")
    assert latest_novelty(tmp_path, EXPERIMENT_ID)["source"] == "agent_research_decision"
    assert read_json(tmp_path / "research/STATE.json")["next_action"]["mode"] == (
        "audit_experiment_plan"
    )


@pytest.mark.parametrize("defect", ["high", "missing_evidence"])
def test_novelty_cannot_be_cleared_by_relabeling(tmp_path, defect):
    _setup(tmp_path, None)
    candidate = _novelty(EXPERIMENT_ID)
    if defect == "high":
        previous = {**candidate, "risk": "high", "decision": "needs_human"}
        append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", previous)
    else:
        candidate["similar_items"] = []
    _respond(tmp_path, "novelty", "record_novelty", novelty=candidate)
    with pytest.raises(ValueError):
        accept_decision(tmp_path, EXPERIMENT_ID, "novelty")


def test_external_limits_and_completion_are_not_research_decisions(tmp_path):
    _setup(tmp_path)
    state_path = tmp_path / "research/STATE.json"
    state = read_json(state_path)
    state.update(stage="full", phase="IMPLEMENTED", next_action={"mode": "implemented"})
    atomic_write_json(state_path, state)
    assert "full-approval-required" in next_agent_led_loop_step(
        tmp_path, explicit_user_request=True,
    )
    state.update(active_experiment=None, latest_completed_experiment=EXPERIMENT_ID,
                 next_action={"mode": "select_experiment"})
    atomic_write_json(state_path, state)
    route = next_agent_led_loop_step(tmp_path, target_id=EXPERIMENT_ID, explicit_user_request=True)
    assert route == f"complete target={EXPERIMENT_ID} next=select_experiment"
    assert next_agent_led_loop_step(
        tmp_path, target_id=EXPERIMENT_ID, explicit_user_request=True,
    ) == route


def test_decision_budget_does_not_spawn_more_workers(tmp_path):
    _setup(tmp_path)
    for index in range(6):
        atomic_write_json(
            tmp_path / f"review/decisions/{EXPERIMENT_ID}/{index}/DISPATCHED.json", {},
        )
        atomic_write_json(
            tmp_path / f"review/decisions/{EXPERIMENT_ID}/{index}/RESPONSE.json", {},
        )
    assert "budget-exhausted" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", explicit_user_request=True,
    )


def test_new_question_does_not_spawn_a_parallel_decision_worker(tmp_path):
    _setup(tmp_path)
    prepare_decision(tmp_path, EXPERIMENT_ID, "plan")
    dispatch_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert "another-decision-worker-pending" in decision_action(
        tmp_path, EXPERIMENT_ID, "plan", question="A different concern", explicit_user_request=True,
    )


def test_revision_budget_preserves_the_locked_plan(tmp_path):
    active = _setup(tmp_path, "fail")
    before = (active / "EXPERIMENT.md").read_bytes()
    for index in range(2):
        atomic_write_json(
            tmp_path / f"review/decisions/{EXPERIMENT_ID}/prior-{index}/ACCEPTED.json",
            {"action": "revise"},
        )
    _respond(tmp_path, "plan", "revise", instructions=["Keep the matched reference."])
    with pytest.raises(ValueError, match="revision budget exhausted"):
        accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    assert (active / "EXPERIMENT.md").read_bytes() == before
    assert read_json(tmp_path / "research/STATE.json")["phase"] == "PLANNED"


def test_saved_stop_is_not_another_vote(tmp_path):
    _setup(tmp_path)
    _respond(tmp_path, "plan", "stop")
    accept_decision(tmp_path, EXPERIMENT_ID, "plan")
    route = next_agent_led_loop_step(tmp_path, explicit_user_request=True)
    assert route.startswith("blocked ") and "outcome=stop" in route


def test_current_request_cannot_select_a_different_target(tmp_path):
    _setup(tmp_path)
    assert "stored-target-mismatch" in next_agent_led_loop_step(
        tmp_path, target_id="EXP-OTHER", explicit_user_request=True,
    )


def _result_response(tmp_path, review_mode="independent"):

    import torch
    from test_comparison_workflow import EXPERIMENT_ID as result_id
    from test_comparison_workflow import _implemented_group

    from scripts.accept_integrity_audit import FIELDS, accept_integrity_audit
    from scripts.run_experiment import execute_experiment

    active = _implemented_group(tmp_path, review_mode)
    record = (active / "EXPERIMENT.md").read_text()
    (active / "EXPERIMENT.md").write_text(
        record.split("## Conclusion")[0]
        + "## Conclusion\n\n## Issues and Next Direction\n",
    )
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        execute_experiment(tmp_path, result_id)
    finally:
        torch.set_num_threads(threads)
    if review_mode == "independent":
        bundle = tmp_path / f"review/bundles/{result_id}"
        text = "# Fixture integrity audit\n\n" + "\n".join(
            f"- {field}: {'pass' if field == 'Verdict' else 'fixture evidence checked'}"
            for field in FIELDS
        )
        (bundle / "INTEGRITY_AUDIT.md").write_text(text + "\n")
        accept_integrity_audit(tmp_path, result_id)
    assert "issue=interpretation" in next_agent_led_loop_step(
        tmp_path, explicit_user_request=True,
    )
    facts = read_json(active / "DECISION_FACTS.json")
    text = f"""## Conclusion

- Decision: inconclusive
- Mechanical rule status: {facts['decision_rule']['status']}
- Decision-rule assessment: this smoke comparison cannot establish research utility
- Primary result: all required cells completed
- Baseline comparison: internal matched reference in every condition
- Supported scope: readiness of the comparison pipeline
- Unsupported or missing evidence: research-scale observations and novel contribution
- Confidence and caveats: limited smoke compute

## Issues and Next Direction

- Main issue: insufficient scientific evidence
- Next action: plan sufficient pilot observations with the same controls
- Stop condition: stop the branch if adequate pilot evidence contradicts the hypothesis
"""
    (active / "RESEARCH_GUIDANCE.md").write_text("EARLIER_AGENT_EXPECTS_SUCCESS")
    request = prepare_decision(tmp_path, result_id, "interpretation")
    assert "EARLIER_AGENT_EXPECTS_SUCCESS" not in request.read_text()
    assert "## Conclusion" not in read_json(request)["sources"][
        f"experiments/active/{result_id}/EXPERIMENT.md"
    ]
    dispatch_decision(tmp_path, result_id, "interpretation")
    bind_worker(tmp_path, result_id, "interpretation", worker_id="fixture-result-worker")
    atomic_write_json(request.parent / "RESPONSE.json", {
        "action": "interpret", "rationale": "Scope follows available observations.",
        "evidence_refs": [f"experiments/active/{result_id}/DECISION_FACTS.json"],
        "assessment": _assessment([f"experiments/active/{result_id}/DECISION_FACTS.json"]),
        "interpretation": text,
    })
    return active, request.parent, text


@pytest.mark.parametrize("review_mode", ["local", "independent"])
def test_inconclusive_agent_result_finalizes_with_original_facts(tmp_path, review_mode):
    from scripts.finalize_experiment import finalize_experiment

    active, folder, text = _result_response(tmp_path, review_mode)
    result_id = active.name
    request = folder / "REQUEST.json"
    original_facts = (active / "DECISION_FACTS.json").read_bytes()
    # Goal-only references cannot stand in for observed result facts.
    response_path = request.parent / "RESPONSE.json"
    valid_response = read_json(response_path)
    atomic_write_json(response_path, {
        **valid_response, "evidence_refs": ["research/GOAL.md"],
        "assessment": _assessment(["research/GOAL.md"]),
    })
    before = (tmp_path / "research/STATE.json").read_bytes()
    with pytest.raises(ValueError, match="authoritative decision facts"):
        accept_decision(tmp_path, result_id, "interpretation")
    assert (tmp_path / "research/STATE.json").read_bytes() == before
    atomic_write_json(response_path, valid_response)
    accept_decision(tmp_path, result_id, "interpretation")
    assert (active / "DECISION_FACTS.json").read_bytes() == original_facts
    assert read_json(active / "MANIFEST.json")["evaluation"]["source"] == (
        "agent_research_decision"
    )
    assert not (tmp_path / f"human/results/{result_id}/INTERPRETATION.md").exists()
    assert "issue=interpretation" not in next_agent_led_loop_step(
        tmp_path, target_id=result_id, explicit_user_request=True,
    )
    finalize_experiment(tmp_path, result_id)
    assert "skill=$maintain-research-memory" in next_agent_led_loop_step(
        tmp_path, target_id=result_id, explicit_user_request=True,
    )


def _protected_bytes(root, active):
    paths = [root / "research/STATE.json", active / "MANIFEST.json", active / "EXPERIMENT.md"]
    paths += [
        active / name
        for name in ("PLAN_AUDIT.md", "INTEGRITY_AUDIT.md", "DECISION_FACTS.json")
        if (active / name).exists()
    ]
    return {path: path.read_bytes() for path in paths}


@pytest.mark.parametrize(
    "defect",
    ["label", "missing_dispatch", "missing_worker", "action", "path", "bytes", "stale_facts"],
)
def test_direct_agent_interpretation_requires_current_exact_proof(tmp_path, defect):
    from scripts.accept_human_interpretation import accept_interpretation

    active, folder, text = _result_response(tmp_path)
    path = folder / "INTERPRETATION.md"
    path.write_text(text)
    if defect == "missing_dispatch":
        (folder / "DISPATCHED.json").unlink()
    elif defect == "missing_worker":
        dispatch = read_json(folder / "DISPATCHED.json")
        del dispatch["worker_id"]
        atomic_write_json(folder / "DISPATCHED.json", dispatch)
    elif defect == "action":
        response = read_json(folder / "RESPONSE.json")
        response["action"] = "stop"
        atomic_write_json(folder / "RESPONSE.json", response)
    elif defect == "path":
        path = folder / "WRONG.md"
        path.write_text(text)
    elif defect == "bytes":
        path.write_text(text + "\n")
    elif defect == "stale_facts":
        facts = read_json(active / "DECISION_FACTS.json")
        facts["unexpected"] = True
        atomic_write_json(active / "DECISION_FACTS.json", facts)
    before = _protected_bytes(tmp_path, active)
    with pytest.raises((ValueError, FileNotFoundError)):
        accept_interpretation(
            tmp_path,
            active.name,
            path,
            source="agent_research_decision",
            decision_path=None if defect == "label" else folder,
        )
    assert _protected_bytes(tmp_path, active) == before
    assert not (folder / "APPLYING.json").exists()


def test_direct_valid_interpretation_records_proof_and_rejects_ready_replay(tmp_path):
    from scripts.accept_human_interpretation import accept_interpretation

    active, folder, text = _result_response(tmp_path)
    path = folder / "INTERPRETATION.md"
    path.write_text(text)
    immutable = {
        name: (active / name).read_bytes()
        for name in (
            "DECISION_FACTS.json",
            "INTEGRITY_AUDIT.md",
            "PLAN_AUDIT.md",
        )
    }
    accept_interpretation(
        tmp_path, active.name, path, source="agent_research_decision", decision_path=folder
    )
    receipt = read_json(folder / "ACCEPTED.json")
    assert receipt == read_json(folder / "APPLYING.json")
    assert read_json(active / "MANIFEST.json")["evaluation"]["decision_provenance"] == receipt
    assert read_json(tmp_path / "research/STATE.json")["phase"] == "READY_TO_FINALIZE"
    before = _protected_bytes(tmp_path, active)
    with pytest.raises(ValueError, match="already accepted"):
        accept_interpretation(
            tmp_path, active.name, path, source="agent_research_decision", decision_path=folder
        )
    assert _protected_bytes(tmp_path, active) == before
    assert {name: (active / name).read_bytes() for name in immutable} == immutable


def _assert_interruption_blocks(root, active):
    from scripts.accept_human_interpretation import accept_interpretation
    from scripts.finalize_experiment import finalize_experiment
    from scripts.next_agent_action import next_agent_action
    from scripts.next_autonomous_step import next_autonomous_step
    from scripts.workflow import set_phase

    before = _protected_bytes(root, active)
    operations = [
        lambda: approve_plan(root, active.name),
        lambda: accept_interpretation(
            root, active.name, root / "human/INTERPRETATION.md", source="human_interpretation"
        ),
        lambda: next_agent_action(root, "implementation", active.name),
        lambda: finalize_experiment(root, active.name),
        lambda: set_phase(root, active.name, "FAILED", objective="must not transition"),
        lambda: next_autonomous_step(root),
        lambda: next_unattended_loop_step(root, explicit_user_request=True),
        lambda: next_agent_led_loop_step(root, explicit_user_request=True),
        lambda: accept_decision(root, active.name, "plan"),
    ]
    for operation in operations:
        with pytest.raises(ValueError, match="decision.*request="):
            operation()
        assert _protected_bytes(root, active) == before


@pytest.mark.parametrize("action", ["approve", "revise", "record_novelty", "interpret"])
@pytest.mark.parametrize(
    "boundary", ["before_write", "after_write", "before_receipt", "after_receipt"]
)
def test_acceptance_interruptions_stop_all_continuations(tmp_path, monkeypatch, action, boundary):
    import importlib

    from scripts.decision_integrity import require_decision_integrity

    if action == "interpret":
        active, folder, _ = _result_response(tmp_path)
        issue = "interpretation"
        module_name, function, name = "scripts.workflow", "atomic_write_json", "STATE.json"
    else:
        active = _setup(tmp_path)
        issue = "novelty" if action == "record_novelty" else "plan"
        extra = (
            {"instructions": "Preserve controls and resolve the missing comparison."}
            if action == "revise"
            else ({"novelty": _novelty(active.name)} if action == "record_novelty" else {})
        )
        folder = _respond(tmp_path, issue, action, **extra)
        module_name, function, name = {
            "approve": ("scripts.approve_plan", "atomic_write_json", "STATE.json"),
            "revise": ("scripts.return_plan_to_draft", "atomic_write_json", "STATE.json"),
            "record_novelty": ("scripts.research_decision", "append_jsonl", "NOVELTY_CHECKS.jsonl"),
        }[action]
    if boundary.endswith("receipt"):
        module_name, function, name = (
            "scripts.research_decision",
            "atomic_write_json",
            "ACCEPTED.json",
        )
    module = importlib.import_module(module_name)
    original = getattr(module, function)

    def interrupted(path, payload):
        if path.name == name and boundary.startswith("before"):
            raise OSError("injected interruption")
        result = original(path, payload)
        if path.name == name and boundary.startswith("after"):
            raise OSError("injected interruption")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(module, function, interrupted)
        with pytest.raises(OSError, match="injected"):
            accept_decision(tmp_path, active.name, issue)
    assert (folder / "APPLYING.json").exists()
    if boundary == "after_receipt":
        require_decision_integrity(tmp_path, active.name)
        assert read_json(folder / "APPLYING.json") == read_json(folder / "ACCEPTED.json")
    else:
        if action in {"revise", "interpret"} and boundary == "after_write":
            assert (
                read_json(tmp_path / "research/STATE.json")["phase"]
                != read_json(active / "MANIFEST.json")["phase"]
            )
        _assert_interruption_blocks(tmp_path, active)


@pytest.mark.parametrize(
    "filename",
    ["REQUEST.json", "RESPONSE.json", "DISPATCHED.json", "ACCEPTED.json", "APPLYING.json"],
)
def test_completed_decision_evidence_remains_guarded_after_snapshot_changes(tmp_path, filename):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    accept_decision(tmp_path, active.name, "plan")
    assert (
        read_json(tmp_path / "research/STATE.json")["next_action"]["mode"] == "implement_experiment"
    )
    value = read_json(folder / filename)
    value["tampered"] = True
    atomic_write_json(folder / filename, value)
    _assert_interruption_blocks(tmp_path, active)


def test_direct_plan_approval_has_receipt_and_cannot_be_replayed(tmp_path):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    approve_plan(tmp_path, active.name, "agent_research_decision", decision_path=folder)
    assert (folder / "ACCEPTED.json").exists()
    before = _protected_bytes(tmp_path, active)
    with pytest.raises(ValueError):
        approve_plan(tmp_path, active.name, "agent_research_decision", decision_path=folder)
    assert _protected_bytes(tmp_path, active) == before


@pytest.mark.parametrize("action", ["approve", "revise", "record_novelty", "invalid"])
def test_invalid_action_payload_never_creates_intent(tmp_path, action):
    active = _setup(tmp_path, "fail" if action == "approve" else "warn")
    issue = "novelty" if action == "record_novelty" else "plan"
    folder = _respond(tmp_path, issue, action)
    before = _protected_bytes(tmp_path, active)
    with pytest.raises(ValueError):
        accept_decision(tmp_path, active.name, issue)
    assert not (folder / "APPLYING.json").exists()
    assert _protected_bytes(tmp_path, active) == before


def test_invalid_interpretation_never_creates_intent(tmp_path):
    active, folder, _ = _result_response(tmp_path)
    response = read_json(folder / "RESPONSE.json")
    response["interpretation"] = "## Conclusion\n- Decision: support\n"
    atomic_write_json(folder / "RESPONSE.json", response)
    before = _protected_bytes(tmp_path, active)
    with pytest.raises(ValueError):
        accept_decision(tmp_path, active.name, "interpretation")
    assert not (folder / "APPLYING.json").exists()
    assert _protected_bytes(tmp_path, active) == before


def test_missing_new_intent_does_not_downgrade_to_legacy(tmp_path):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    accept_decision(tmp_path, active.name, "plan")
    (folder / "APPLYING.json").unlink()
    _assert_interruption_blocks(tmp_path, active)


def test_completed_interpretation_evidence_is_checked_in_ready_phase(tmp_path):
    active, folder, _ = _result_response(tmp_path)
    accept_decision(tmp_path, active.name, "interpretation")
    assert read_json(tmp_path / "research/STATE.json")["phase"] == "READY_TO_FINALIZE"
    response = read_json(folder / "RESPONSE.json")
    response["interpretation"] += "\nAltered after acceptance.\n"
    atomic_write_json(folder / "RESPONSE.json", response)
    _assert_interruption_blocks(tmp_path, active)


def test_malformed_intent_reports_request_for_inspection(tmp_path):
    active = _setup(tmp_path)
    folder = _respond(tmp_path, "plan", "approve")
    accept_decision(tmp_path, active.name, "plan")
    (folder / "APPLYING.json").write_text("{broken")
    _assert_interruption_blocks(tmp_path, active)


@pytest.mark.parametrize(
    "defect",
    ["two_files", "saved_interpretation", "evaluation", "conclusion", "issues",
     "provenance", "missing_provenance", "decision", "path", "source"],
)
def test_accepted_materialization_must_match_attributed_response(tmp_path, defect):
    from scripts.finalize_experiment import finalize_experiment
    from scripts.next_agent_action import next_agent_action

    active, folder, _ = _result_response(tmp_path)
    accept_decision(tmp_path, active.name, "interpretation")
    immutable = {name: (active / name).read_bytes() for name in (
        "DECISION_FACTS.json", "PLAN_AUDIT.md", "INTEGRITY_AUDIT.md",
    )}
    paths = {
        "two_files": [active / "EXPERIMENT.md", active / "EVALUATION.md"],
        "saved_interpretation": [folder / "INTERPRETATION.md"],
        "evaluation": [active / "EVALUATION.md"],
        "conclusion": [active / "EXPERIMENT.md"],
        "issues": [active / "EXPERIMENT.md"],
    }.get(defect)
    if paths is not None:
        for path in paths:
            text = path.read_text()
            text = text.replace("insufficient scientific evidence", "a different issue") if (
                defect == "issues"
            ) else text.replace("Decision: inconclusive", "Decision: reject")
            path.write_text(text)
    else:
        manifest = read_json(active / "MANIFEST.json")
        evaluation = manifest["evaluation"]
        if defect == "provenance":
            evaluation["decision_provenance"]["worker_id"] = "changed-worker"
        elif defect == "missing_provenance":
            del evaluation["decision_provenance"]
        elif defect == "decision":
            evaluation["decision"] = "reject"
        elif defect == "path":
            evaluation["path"] = "unrelated/INTERPRETATION.md"
        else:
            evaluation["source"] = "human_interpretation"
        atomic_write_json(active / "MANIFEST.json", manifest)
    before = {
        **_protected_bytes(tmp_path, active),
        active / "EVALUATION.md": (active / "EVALUATION.md").read_bytes(),
        **{folder / name: (folder / name).read_bytes() for name in (
            "INTERPRETATION.md", "REQUEST.json", "RESPONSE.json", "DISPATCHED.json",
            "APPLYING.json", "ACCEPTED.json",
        )},
    }
    for operation in (
        lambda: next_agent_action(tmp_path, "evaluation", active.name),
        lambda: next_agent_led_loop_step(tmp_path, explicit_user_request=True),
        lambda: finalize_experiment(tmp_path, active.name),
    ):
        with pytest.raises(ValueError, match="changed decision materialization: request="):
            operation()
        assert {path: path.read_bytes() for path in before} == before
        assert not (tmp_path / "experiments/completed" / active.name).exists()
    assert {name: (active / name).read_bytes() for name in immutable} == immutable


def test_materialization_guard_does_not_freeze_other_record_sections(tmp_path):
    from scripts.finalize_experiment import finalize_experiment
    from scripts.next_agent_action import next_agent_action

    active, folder, _ = _result_response(tmp_path)
    accept_decision(tmp_path, active.name, "interpretation")
    record = active / "EXPERIMENT.md"
    record.write_text("Record annotation outside the copied sections.\n\n" + record.read_text())
    assert next_agent_action(tmp_path, "evaluation", active.name) == "action=finalize"
    completed = finalize_experiment(tmp_path, active.name)
    assert (completed / "EXPERIMENT.md").read_text().startswith("Record annotation")


def test_explicit_human_replacement_updates_attribution_and_can_finalize(tmp_path):
    from scripts.accept_human_interpretation import accept_human_interpretation
    from scripts.finalize_experiment import finalize_experiment
    from scripts.next_agent_action import next_agent_action

    active, folder, text = _result_response(tmp_path)
    accept_decision(tmp_path, active.name, "interpretation")
    immutable = {
        name: (active / name).read_bytes()
        for name in (
            "DECISION_FACTS.json",
            "PLAN_AUDIT.md",
            "INTEGRITY_AUDIT.md",
        )
    }
    receipt = (folder / "ACCEPTED.json").read_bytes()
    response = (folder / "RESPONSE.json").read_bytes()
    path = tmp_path / "human/results" / active.name / "INTERPRETATION.md"
    path.parent.mkdir(parents=True)
    replacement = text.replace("Decision: inconclusive", "Decision: reject")
    replacement += "\n## Japanese Notes\n\nHuman replacement notes.\n"
    path.write_text(replacement)
    accept_human_interpretation(tmp_path, active.name)
    evaluation = read_json(active / "MANIFEST.json")["evaluation"]
    assert evaluation == {
        "source": "human_interpretation",
        "decision": "reject",
        "path": path.relative_to(tmp_path).as_posix(),
    }
    assert (active / "EVALUATION.md").read_text() == replacement
    # Historical agent materialization is no longer the current evaluation.
    (folder / "INTERPRETATION.md").write_text("Historical sidecar changed after replacement.\n")
    assert next_agent_action(tmp_path, "evaluation", active.name) == "action=finalize"
    completed = finalize_experiment(tmp_path, active.name)
    assert "Decision: reject" in (completed / "EXPERIMENT.md").read_text()
    assert {name: (completed / name).read_bytes() for name in immutable} == immutable
    assert (folder / "ACCEPTED.json").read_bytes() == receipt
    assert (folder / "RESPONSE.json").read_bytes() == response


def test_historical_interpretation_without_new_receipt_schema_remains_compatible(tmp_path):
    from scripts.next_agent_action import next_agent_action

    active, folder, _ = _result_response(tmp_path)
    accept_decision(tmp_path, active.name, "interpretation")
    receipt = read_json(folder / "ACCEPTED.json")
    del receipt["acceptance_version"]
    del receipt["dispatch_sha256"]
    atomic_write_json(folder / "ACCEPTED.json", receipt)
    (folder / "APPLYING.json").unlink()
    manifest = read_json(active / "MANIFEST.json")
    del manifest["evaluation"]["decision_provenance"]
    atomic_write_json(active / "MANIFEST.json", manifest)
    assert next_agent_action(tmp_path, "evaluation", active.name) == "action=finalize"
