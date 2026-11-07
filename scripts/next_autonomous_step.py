from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_review_bundle import (
    IntegrityAuditRequiredError,
    require_accepted_integrity_audit,
)
from scripts.common import (
    QuietArgumentParser,
    one_line,
    read_json,
    root_from_script,
    run_script,
)
from scripts.decision_integrity import require_routing_integrity
from scripts.next_agent_action import next_agent_action
from scripts.research_memory import (
    latest_novelty,
    novelty_contract_required,
    novelty_evidence_errors,
)

MODE_TO_SKILL = {
    "initial_setup": "$initial-setup",
    "plan_experiment": "$plan-experiment",
    "audit_experiment_plan": "$audit-experiment-plan",
    "review_experiment_plan": "$review-experiment-plan",
    "revise_experiment_plan": "$revise-experiment-plan",
    "implement_experiment": "$implement-experiment",
    "review_implementation": "$audit-experiment-implementation",
    "implemented": "$run-experiment",
    "sanity_passed": "$run-experiment",
    "trained": "$run-experiment",
    "review_required": "$evaluate-experiment",
    "ready_to_finalize": "$evaluate-experiment",
    "debug_failure": "$debug-failure",
    "maintain_memory": "$maintain-research-memory",
    "update_direction": "$update-research-direction",
    "select_experiment": "$select-next-experiment",
}

MODE_TO_OPERATION = {
    "initial_setup": "setup",
    "plan_experiment": "planning",
    "audit_experiment_plan": "planning",
    "review_experiment_plan": "human_plan_review",
    "revise_experiment_plan": "planning",
    "implement_experiment": "implementation",
    "review_implementation": "implementation_review",
    "implemented": "execution",
    "sanity_passed": "execution",
    "trained": "execution",
    "review_required": "result_review",
    "ready_to_finalize": "result_review",
    "debug_failure": "repair",
    "maintain_memory": "post_result",
    "update_direction": "post_result",
    "select_experiment": "post_result",
}

MAX_OPERATION_PHASES = 3

BLOCKED_MODES = {
    "review_experiment_plan": "human approval, revision, or defer decision is required",
}
AGENT_PREFLIGHT_TASKS = {
    "plan_experiment": "planning",
    "implement_experiment": "implementation",
    "debug_failure": "repair",
}
ACTIVE_REQUIRED_MODES = {
    "plan_experiment",
    "audit_experiment_plan",
    "review_experiment_plan",
    "revise_experiment_plan",
    "implement_experiment",
    "review_implementation",
    "implemented",
    "sanity_passed",
    "trained",
    "review_required",
    "ready_to_finalize",
    "debug_failure",
}


def review_skill(root: Path, experiment_id: str) -> str:
    active = root / "experiments/active" / experiment_id
    manifest = read_json(active / "MANIFEST.json")
    try:
        require_accepted_integrity_audit(root, active, manifest)
    except IntegrityAuditRequiredError:
        return "$audit-experiment-integrity"
    return "$evaluate-experiment"


def novelty_block_reason(root: Path, experiment_id: str) -> str | None:
    manifest_path = root / "experiments/active" / experiment_id / "MANIFEST.json"
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    require_contribution = novelty_contract_required(manifest)
    record = latest_novelty(root, experiment_id)
    if record is None:
        return "missing-novelty-check"
    risk = record.get("risk")
    decision = record.get("decision")
    if record.get("human_review_needed") is True:
        return "novelty-human-review-needed"
    if risk in ("high", "block"):
        return f"novelty-risk-{risk}"
    if risk not in ("low", "medium") or decision != "proceed":
        return "novelty-not-cleared"
    if novelty_evidence_errors(record, require_contribution=require_contribution):
        return "novelty-evidence-incomplete"
    return None


def missing_novelty_preparation(mode: str, phase: str | None, reason: str | None) -> bool:
    return (
        mode == "audit_experiment_plan" and phase == "PLANNED"
        and reason == "missing-novelty-check"
    )


def full_approval_required(state: dict, experiment_id: str) -> bool:
    return (
        str(state.get("stage", "")).lower() == "full"
        and state.get("next_action", {}).get("mode") in {"implemented", "sanity_passed"}
        and state.get("approvals", {}).get("full_training_experiment_id") != experiment_id
    )


def next_autonomous_step(root: Path) -> str:
    state = read_json(root / "research/STATE.json")
    require_routing_integrity(root, state)
    mode = str(state.get("next_action", {}).get("mode", "unknown"))
    objective = str(state.get("next_action", {}).get("objective", "unknown"))
    active = state.get("active_experiment") or "none"
    phase = state.get("phase")
    skill = MODE_TO_SKILL.get(mode)
    operation = MODE_TO_OPERATION.get(mode)
    if mode == "review_required" and active != "none":
        skill = review_skill(root, str(active))
    if skill is None or operation is None:
        return f"blocked mode={mode} reason=unknown-next-action"
    if mode in {"maintain_memory", "update_direction", "select_experiment"} and active != "none":
        return (
            f"blocked mode={mode} operation={operation} skill={skill} "
            f"active={active} reason=unexpected-active-experiment"
        )
    if mode in ACTIVE_REQUIRED_MODES and active == "none":
        return (
            f"blocked mode={mode} operation={operation} skill={skill} "
            "reason=no-active-experiment"
        )
    if active != "none" and phase in {"DRAFT", "PLANNED"} and mode in {
        "audit_experiment_plan",
        "review_experiment_plan",
        "implement_experiment",
    }:
        reason = novelty_block_reason(root, str(active))
        if missing_novelty_preparation(mode, phase, reason):
            return (
                f"ready mode={mode} operation=planning max_phases={MAX_OPERATION_PHASES} "
                f"skill=$audit-novelty active={active} action=prepare-novelty "
                "prompt=Run the bounded novelty audit once, then reroute. "
                "The new evidence record is progress without a phase change; "
                "stop if no usable evidence or required human judgment remains."
            )
        if reason is not None:
            return (
                f"blocked mode={mode} operation={operation} skill={skill} "
                f"active={active} reason={reason}"
            )
    if mode in BLOCKED_MODES:
        return (
            f"blocked mode={mode} operation={operation} skill={skill} "
            f"reason={BLOCKED_MODES[mode]}"
        )
    if full_approval_required(state, str(active)):
        return (
            f"blocked mode={mode} operation={operation} skill={skill} "
            f"active={active} reason=full-approval-required"
        )
    preflight_task = AGENT_PREFLIGHT_TASKS.get(mode)
    if preflight_task is not None:
        try:
            preflight = next_agent_action(root, preflight_task, str(active))
        except (OSError, KeyError, TypeError, ValueError) as exc:
            return (
                f"blocked mode={mode} operation={operation} skill={skill} "
                f"reason=agent-preflight-{type(exc).__name__} "
                f"detail={one_line(exc)[:200]}"
            )
        if preflight.startswith("action=blocked "):
            return (
                f"blocked mode={mode} operation={operation} skill={skill} "
                f"active={active} {preflight.removeprefix('action=blocked ')}"
            )
        expected_action = (
            ("action=build ", "action=delegate ")
            if preflight_task == "repair"
            else "action=delegate "
        )
        if not preflight.startswith(expected_action):
            return (
                f"blocked mode={mode} operation={operation} skill={skill} "
                f"reason=agent-preflight-not-delegated detail={preflight}"
            )
    if mode == "debug_failure":
        objective = "Use the isolated repair gate; keep source and debugging history in its worker."
    prompt = (
        f"Read research/CONTEXT.md and research/STATE.json. Use {skill} for the current "
        f"phase of operation={operation}: {objective}. Active experiment: {active}. "
        "After the phase, rerun this router. Continue for at most "
        f"{MAX_OPERATION_PHASES} phases while it returns ready with operation={operation}; "
        "state, evidence files or a changed gate action can demonstrate progress; "
        "recover presentation errors within the phase using automation/PRESENTATION_REPAIR.md; "
        "stop on an operation change, substantive block/failure, "
        "no progress after correction, or request for human judgment."
    )
    return (
        f"ready mode={mode} operation={operation} "
        f"max_phases={MAX_OPERATION_PHASES} skill={skill} "
        f"active={active} prompt={prompt}"
    )


def _execute() -> str:
    QuietArgumentParser(description="Print the next autonomous research-loop step.").parse_args()
    return next_autonomous_step(root_from_script())


if __name__ == "__main__":
    raise SystemExit(run_script("next-autonomous-step", _execute))
