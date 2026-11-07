"""Separate opt-in route with delegated scientific decisions, one target only."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, read_json, root_from_script, run_script
from scripts.next_agent_action import next_agent_action
from scripts.next_unattended_loop_step import next_unattended_loop_step
from scripts.research_decision import decision_action


def next_agent_led_loop_step(
    root: Path, *, target_id: str | None = None, explicit_user_request: bool = False,
) -> str:
    if not explicit_user_request:
        return "blocked reason=explicit-agent-led-request-required"
    route = next_unattended_loop_step(
        root, target_id=target_id, explicit_user_request=True, control_key="agent_led_loop",
    )
    state = read_json(root / "research/STATE.json")
    target = state.get("agent_led_loop", {}).get("target_experiment")
    if target is None or route.startswith("complete "):
        return route
    if target_id is not None and target_id != target:
        return route
    mode = state.get("next_action", {}).get("mode")
    issue = None
    if "reason=novelty-" in route or "reason=missing-novelty-check" in route or (
        "skill=$audit-novelty" in route
    ):
        issue = "novelty"
    elif mode == "review_experiment_plan" and (
        "action=approve-plan" in route or "reason=plan-audit-pass-required" in route
    ):
        issue = "plan"
    elif route.startswith("ready ") and "skill=$evaluate-experiment" in route:
        manifest = read_json(root / "experiments/active" / target / "MANIFEST.json")
        if manifest.get("evaluation") is None:
            gate = next_agent_action(root, "evaluation", target)
            if gate.startswith(("action=build ", "action=finalize")):
                return f"ready mode={mode} target={target} skill=$evaluate-experiment {gate}"
            issue = "interpretation"
    if issue is not None:
        gate = decision_action(root, target, issue, explicit_user_request=True)
        status = "blocked" if gate.startswith("action=blocked ") else "ready"
        return (
            f"{status} mode={mode} target={target} skill=$run-one-agent-led-loop "
            f"issue={issue} {gate}"
        )
    if route.startswith("ready ") and mode == "revise_experiment_plan":
        gate = next_agent_action(root, "planning", target)
        return f"ready mode={mode} target={target} skill=$plan-experiment {gate}"
    return route


def _execute() -> str:
    parser = QuietArgumentParser(description="Route one loop with delegated research judgment.")
    parser.add_argument("--target", dest="target_id")
    parser.add_argument("--explicit-user-request", action="store_true")
    args = parser.parse_args()
    return next_agent_led_loop_step(
        root_from_script(), target_id=args.target_id,
        explicit_user_request=args.explicit_user_request,
    )


if __name__ == "__main__":
    raise SystemExit(run_script("next-agent-led-loop-step", _execute))
