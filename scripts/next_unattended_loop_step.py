from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_plan_review_bundle import (
    PlanAuditRequiredError,
    require_accepted_plan_audit,
)
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    one_line,
    read_json,
    root_from_script,
    run_script,
)
from scripts.decision_integrity import require_routing_integrity
from scripts.next_agent_action import next_agent_action
from scripts.next_autonomous_step import (
    MODE_TO_SKILL,
    full_approval_required,
    missing_novelty_preparation,
    novelty_block_reason,
    review_skill,
)

POST_RESULT_MODES = {"maintain_memory", "update_direction"}


def has_ready_hypothesis(root: Path) -> bool:
    queue = read_json(root / "research/QUEUE.json")
    for item in queue["items"]:
        if item.get("status") not in {"draft", "ready", "queued"}:
            continue
        if item.get("forbidden_by_policy", False):
            continue
        fields = ("id", "hypothesis", "falsifier", "minimal_test", "primary_metric")
        if all(
            isinstance(item.get(key), str)
            and item[key].strip()
            and not re.search(r"<[A-Za-z][^>\n]*>", item[key])
            for key in fields
        ):
            return True
    return False


def _record_progress(
    root: Path,
    state: dict,
    *,
    status: str,
    target: str | None,
    last_mode: str,
    control_key: str = "unattended_loop",
) -> None:
    state[control_key] = {
        "status": status,
        "target_experiment": target,
        "last_mode": last_mode,
    }
    atomic_write_json(root / "research/STATE.json", state)


def next_unattended_loop_step(
    root: Path,
    *,
    target_id: str | None = None,
    explicit_user_request: bool = False,
    control_key: str = "unattended_loop",
) -> str:
    if not explicit_user_request:
        return "blocked reason=explicit-user-request-required"
    if control_key not in {"unattended_loop", "agent_led_loop"}:
        raise ValueError("unknown loop control")

    state = read_json(root / "research/STATE.json")
    require_routing_integrity(root, state)
    mode = str(state.get("next_action", {}).get("mode", "unknown"))
    active = state.get("active_experiment")
    latest = state.get("latest_completed_experiment")
    phase = state.get("phase")

    if mode == "initial_setup":
        return "blocked reason=initial-setup-requires-human-input"
    if mode == "debug_failure" or phase == "FAILED":
        return "blocked reason=failed-experiment-requires-separate-repair"

    control = state.get(control_key, {})
    stored_target = (
        str(control.get("target_experiment"))
        if control.get("status") == "in_progress"
        and control.get("target_experiment")
        else None
    )
    if (
        stored_target is not None
        and active is not None
        and str(active) != stored_target
        and latest == stored_target
    ):
        _record_progress(
            root, state, status="idle", target=None, last_mode=mode, control_key=control_key,
        )
        stored_target = None
    if (
        target_id is not None
        and stored_target is not None
        and target_id != stored_target
    ):
        return f"blocked mode={mode} target={target_id} reason=stored-target-mismatch"
    target = target_id or stored_target
    if target is None:
        if active:
            target = str(active)
        elif mode in POST_RESULT_MODES and latest:
            target = str(latest)
        elif mode == "select_experiment":
            if not has_ready_hypothesis(root):
                if control.get("last_mode") == "replenish_hypotheses":
                    return "blocked mode=select_experiment reason=no-viable-hypothesis"
                _record_progress(
                    root,
                    state,
                    status="idle",
                    target=None,
                    last_mode="replenish_hypotheses",
                    control_key=control_key,
                )
                return (
                    "ready mode=select_experiment target=pending "
                    "action=replenish-hypotheses skill=$replenish-research-hypotheses"
                )
            return (
                "ready mode=select_experiment target=pending action=create-target "
                "skill=$select-next-experiment"
            )
        else:
            return f"blocked mode={mode} reason=no-loop-target"

    if active is not None and str(active) != target:
        return f"blocked mode={mode} target={target} reason=active-experiment-mismatch"

    if mode == "select_experiment":
        if active is not None:
            return f"blocked mode={mode} target={target} reason=invalid-active-state"
        if latest == target:
            _record_progress(
                root, state, status="idle", target=None, last_mode=mode, control_key=control_key,
            )
            return f"complete target={target} next=select_experiment"
        return f"blocked mode={mode} target={target} reason=target-not-completed"

    if mode in POST_RESULT_MODES:
        if latest != target:
            return f"blocked mode={mode} target={target} reason=completed-target-mismatch"
    elif active != target:
        return f"blocked mode={mode} target={target} reason=target-not-active"

    _record_progress(
        root, state, status="in_progress", target=target, last_mode=mode, control_key=control_key,
    )
    if full_approval_required(state, target):
        return f"blocked mode={mode} target={target} reason=full-approval-required"

    if phase in {"DRAFT", "PLANNED"} and mode in {
        "audit_experiment_plan",
        "review_experiment_plan",
        "implement_experiment",
    }:
        reason = novelty_block_reason(root, target)
        if missing_novelty_preparation(mode, phase, reason):
            return (
                f"ready mode={mode} target={target} action=run-phase "
                "skill=$audit-novelty preparation=missing-novelty-check"
            )
        if reason is not None:
            return f"blocked mode={mode} target={target} reason={reason}"

    if mode == "review_experiment_plan":
        if phase != "PLANNED":
            return f"blocked mode={mode} target={target} reason=invalid-plan-phase"
        manifest = read_json(
            root / "experiments/active" / target / "MANIFEST.json"
        )
        try:
            require_accepted_plan_audit(
                root,
                root / "experiments/active" / target,
                manifest,
                allow_warn=False,
            )
        except PlanAuditRequiredError:
            return f"blocked mode={mode} target={target} reason=plan-audit-pass-required"
        return (
            f"ready mode={mode} target={target} action=approve-plan "
            "source=explicit_unattended_loop"
        )

    skill = MODE_TO_SKILL.get(mode)
    if mode == "review_required":
        skill = review_skill(root, target)
    if skill is None:
        return f"blocked mode={mode} target={target} reason=unknown-next-action"
    preflight_task = {
        "plan_experiment": "planning",
        "implement_experiment": "implementation",
    }.get(mode)
    if preflight_task is not None:
        try:
            preflight = next_agent_action(root, preflight_task, target)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            return (
                f"blocked mode={mode} target={target} "
                f"reason=agent-preflight-{type(exc).__name__} detail={one_line(exc)[:200]}"
            )
        if not preflight.startswith("action=delegate "):
            return (
                f"blocked mode={mode} target={target} "
                f"reason=agent-preflight-not-delegated"
            )
    return f"ready mode={mode} target={target} action=run-phase skill={skill}"


def _execute() -> str:
    parser = QuietArgumentParser(description="Route one explicitly authorized unattended loop.")
    parser.add_argument("--target", dest="target_id")
    parser.add_argument("--explicit-user-request", action="store_true")
    args = parser.parse_args()
    return next_unattended_loop_step(
        root_from_script(),
        target_id=args.target_id,
        explicit_user_request=args.explicit_user_request,
    )


if __name__ == "__main__":
    raise SystemExit(run_script("next-unattended-loop-step", _execute))
