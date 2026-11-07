from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dl_research.experiment.comparison import require_comparison_budget
from scripts.build_decision_facts import (
    DecisionFactsRequiredError,
    require_current_decision_facts,
)
from scripts.build_implementation_review_bundle import (
    implementation_audit_input_hashes,
    implementation_review_required,
)
from scripts.build_plan_review_bundle import (
    plan_audit_input_hashes,
    require_accepted_plan_audit,
)
from scripts.build_review_bundle import (
    audit_input_hashes,
    require_accepted_integrity_audit,
)
from scripts.common import (
    QuietArgumentParser,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.compress_audit_material import material_action
from scripts.implementation_delta import require_locked_implementation_delta
from scripts.records import field, plan_hash, validate_plan
from scripts.repair_context import repair_request, request_path
from scripts.scope import validate_scope
from scripts.workflow import comparison_results_recorded, require_active

TASKS = {
    "planning",
    "implementation",
    "plan-audit",
    "implementation-audit",
    "integrity-audit",
    "evaluation",
    "repair",
}
TASK_FIELDS = {
    "plan-audit": (
        "Verdict",
        "Goal-metric alignment",
        "Research scale adequacy",
        "Metric gaming path",
        "Selection and evaluation separation",
        "Baseline comparability",
        "Metric discipline",
        "Intervention clarity",
        "Implementation profile fit",
        "Minimal guardrail",
        "Blocking issue",
        "Required action",
    ),
    "implementation-audit": (
        "Verdict",
        "Plan fidelity",
        "Data split and leakage",
        "Loss and optimization",
        "Metric implementation",
        "Reproducibility and checkpointing",
        "Scope and minimality",
        "Declared implementation delta",
        "Blocking issue",
        "Required action",
    ),
    "integrity-audit": (
        "Verdict",
        "Result provenance",
        "Plan adherence",
        "Metric validity",
        "Data leakage and split risk",
        "Scope discipline",
        "Blocking issue",
        "Required action",
    ),
    "evaluation": (
        "Decision",
        "Mechanical rule status",
        "Decision-rule assessment",
        "Primary result",
        "Baseline comparison",
        "Supported scope",
        "Unsupported or missing evidence",
        "Confidence and caveats",
        "Main issue",
        "Next action",
        "Stop recommendation",
    ),
    "record-evaluation": (
        "Decision",
        "Mechanical rule status",
        "Decision-rule assessment",
        "Primary result",
        "Baseline comparison",
        "Supported scope",
        "Unsupported or missing evidence",
        "Confidence and caveats",
        "Main issue",
        "Next action",
        "Stop condition",
    ),
}
PROFILE_AGENTS = {
    "mechanical": "mechanical_implementer",
    "balanced": "experiment_implementer",
    "frontier": "scientific_implementer",
}


def _require_mode(
    root: Path,
    experiment_id: str,
    phases: set[str],
    mode: str | set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    state, manifest = require_active(root, experiment_id, phases)
    allowed = {mode} if isinstance(mode, str) else mode
    if state.get("next_action", {}).get("mode") not in allowed:
        raise ValueError(f"next action is not {mode}")
    return state, manifest


def _scope(root: Path, state: dict[str, Any], active: Path) -> tuple[dict, list[str]]:
    budgets = state.get("budgets", {})
    return validate_scope(
        root,
        read_json(active / "SCOPE.json"),
        maximum_files=int(budgets.get("max_scope_files", 10)),
        maximum_planning_python_reads=int(
            budgets.get("max_planning_python_reads", 3)
        ),
        maximum_implementation_entry_python_reads=int(
            budgets.get("max_implementation_entry_python_reads", 3)
        ),
    )


def _planning_action(root: Path, experiment_id: str) -> str:
    state, manifest = _require_mode(
        root,
        experiment_id,
        {"DRAFT"},
        {"plan_experiment", "revise_experiment_plan"},
    )
    if state.get("project_status") != "active":
        raise ValueError("planning requires an active project")
    active = root / "experiments/active" / experiment_id
    for name in ("EXPERIMENT.md", "SCOPE.json", "MANIFEST.json"):
        if not (active / name).is_file():
            raise FileNotFoundError(f"active planning file is missing: {name}")
    config = read_json(root / manifest["config"])
    experiment = config.get("experiment", {})
    if experiment.get("id") != experiment_id:
        raise ValueError("config experiment ID does not match")
    if experiment.get("stage") != manifest.get("stage"):
        raise ValueError("config stage does not match experiment manifest")
    _scope(root, state, active)
    goal = (root / "research/GOAL.md").read_text(encoding="utf-8")
    if re.search(r"<[A-Za-z][^>\n]*>", goal):
        raise ValueError("research goal still contains setup placeholders")
    return "action=delegate agent=research_planner"


def _implementation_action(root: Path, experiment_id: str) -> str:
    state, manifest = _require_mode(
        root,
        experiment_id,
        {"PLANNED"},
        "implement_experiment",
    )
    if state.get("approvals", {}).get("plan_review_experiment_id") != experiment_id:
        raise ValueError("recorded plan approval is required")
    if manifest.get("plan_review", {}).get("status") != "approved":
        raise ValueError("approved plan review record is required")
    active = root / "experiments/active" / experiment_id
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    record_path = active / "EXPERIMENT.md"
    config_path = root / manifest["config"]
    scope_path = active / "SCOPE.json"
    record = record_path.read_text(encoding="utf-8")
    validate_plan(record, stage=manifest.get("stage"))
    require_comparison_budget(read_json(config_path), state)
    if plan_hash(record_path, config_path, scope_path) != manifest.get("plan_sha256"):
        raise ValueError("locked plan, config, or scope changed")
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    _, scope_files = _scope(root, state, active)
    if scope_files != manifest.get("scope_files"):
        raise ValueError("validated scope differs from locked scope")
    require_locked_implementation_delta(root, active, manifest)
    profile = field(record, "Implementation profile").lower()
    agent = PROFILE_AGENTS.get(profile)
    if agent is None:
        raise ValueError("unknown implementation profile")
    return f"action=delegate agent={agent} profile={profile}"


def _document_state(path: Path, labels: tuple[str, ...]) -> str:
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8")
    filled = 0
    for label in labels:
        try:
            value = field(text, label).strip().lower()
        except ValueError:
            return "malformed"
        if value and value != "pending" and not value.startswith("<"):
            filled += 1
    if filled == 0:
        return "template"
    if filled == len(labels):
        return "complete"
    return "partial"


def _request_is_current(path: Path, hashes: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        request = read_json(path)
    except (OSError, ValueError):
        return False
    return request.get("audited_input_hashes") == hashes


def _review_document_action(
    path: Path,
    task: str,
    *,
    acceptor: str,
    agent: str,
) -> str:
    status = _document_state(path, TASK_FIELDS[task])
    if status == "complete":
        return f"action=accept acceptor={acceptor}"
    if status == "template":
        return f"action=delegate agent={agent}"
    return f"action=blocked reason={status}-review-output"


def _plan_audit_action(root: Path, experiment_id: str) -> str:
    state, manifest = _require_mode(
        root,
        experiment_id,
        {"PLANNED"},
        "audit_experiment_plan",
    )
    require_comparison_budget(read_json(root / manifest["config"]), state)
    active = root / "experiments/active" / experiment_id
    require_locked_implementation_delta(root, active, manifest)
    bundle = root / "review/bundles" / f"{experiment_id}-plan"
    current = plan_audit_input_hashes(root, active, manifest)
    if not _request_is_current(bundle / "PLAN_AUDIT_REQUEST.json", current):
        return "action=build builder=build_plan_review_bundle"
    action = _review_document_action(
        bundle / "PLAN_AUDIT.md",
        "plan-audit",
        acceptor="accept_plan_audit",
        agent="plan_auditor",
    )
    if action.startswith(("action=accept ", "action=delegate ")):
        return material_action(root, state, bundle, experiment_id, "plan-audit") or action
    return action


def _implementation_audit_action(root: Path, experiment_id: str) -> str:
    state, manifest = _require_mode(
        root,
        experiment_id,
        {"IMPLEMENTED"},
        "review_implementation",
    )
    if not implementation_review_required(state, manifest):
        raise ValueError("implementation review is not required")
    active = root / "experiments/active" / experiment_id
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    bundle = root / "review/bundles" / experiment_id
    current = implementation_audit_input_hashes(root, active, manifest)
    if not _request_is_current(bundle / "IMPLEMENTATION_REQUEST.json", current):
        return "action=build builder=build_implementation_review_bundle"
    action = _review_document_action(
        bundle / "IMPLEMENTATION_AUDIT.md",
        "implementation-audit",
        acceptor="accept_implementation_audit",
        agent="evaluator",
    )
    if action.startswith(("action=accept ", "action=delegate ")):
        return material_action(root, state, bundle, experiment_id, "implementation-audit") or action
    return action


def _integrity_audit_action(root: Path, experiment_id: str) -> str:
    state, manifest = _require_mode(
        root,
        experiment_id,
        {"REVIEW_REQUIRED"},
        "review_required",
    )
    active = root / "experiments/active" / experiment_id
    try:
        require_accepted_integrity_audit(root, active, manifest)
    except ValueError:
        pass
    else:
        return "action=complete next=evaluation"
    bundle = root / "review/bundles" / experiment_id
    try:
        current = audit_input_hashes(root, active, manifest)
    except (OSError, ValueError):
        return "action=build builder=build_review_bundle"
    if not _request_is_current(bundle / "INTEGRITY_REQUEST.json", current):
        return "action=build builder=build_review_bundle"
    action = _review_document_action(
        bundle / "INTEGRITY_AUDIT.md",
        "integrity-audit",
        acceptor="accept_integrity_audit",
        agent="evaluator",
    )
    if action.startswith(("action=accept ", "action=delegate ")):
        return material_action(root, state, bundle, experiment_id, "integrity-audit") or action
    return action


def _evaluation_action(root: Path, experiment_id: str) -> str:
    state, manifest = require_active(
        root,
        experiment_id,
        {"REVIEW_REQUIRED", "READY_TO_FINALIZE"},
    )
    active = root / "experiments/active" / experiment_id
    config = read_json(root / manifest["config"])
    review_mode = config.get("experiment", {}).get("review_mode")
    try:
        facts = require_current_decision_facts(root, active, manifest)
    except DecisionFactsRequiredError:
        if state.get("phase") == "READY_TO_FINALIZE" and review_mode != "independent":
            return "action=build builder=build_decision_facts"
        return "action=blocked reason=missing-or-stale-decision-facts"
    if state.get("phase") == "READY_TO_FINALIZE":
        if state.get("next_action", {}).get("mode") != "ready_to_finalize":
            raise ValueError("evaluation is not ready to finalize")
        if review_mode == "independent":
            require_accepted_integrity_audit(root, active, manifest)
        status = _document_state(
            active / "EXPERIMENT.md",
            TASK_FIELDS["record-evaluation"],
        )
        if status == "complete":
            return "action=finalize"
        if status == "template" and review_mode != "independent":
            return (
                "action=local "
                f"rule_status={facts['decision_rule']['status']}"
            )
        return f"action=blocked reason={status}-record-evaluation"
    if review_mode != "independent":
        raise ValueError("local evaluation has an invalid phase")
    if state.get("next_action", {}).get("mode") != "review_required":
        raise ValueError("independent evaluation is not in review_required mode")
    require_accepted_integrity_audit(root, active, manifest)
    bundle = root / "review/bundles" / experiment_id
    bundled_facts = bundle / "DECISION_FACTS.json"
    if not bundled_facts.is_file() or sha256_file(bundled_facts) != sha256_file(
        active / "DECISION_FACTS.json"
    ):
        return "action=blocked reason=stale-decision-facts-bundle"
    return _review_document_action(
        bundle / "EVALUATION.md",
        "evaluation",
        acceptor="accept_evaluation",
        agent="evaluator",
    )


def _repair_action(root: Path, experiment_id: str) -> str:
    _, manifest = _require_mode(root, experiment_id, {"FAILED"}, "debug_failure")
    if comparison_results_recorded(root, manifest):
        return "action=blocked reason=recorded-comparison-requires-human-disposition"
    request = repair_request(root, experiment_id)
    path = request_path(root, experiment_id, request["sequence"])
    if not path.is_file() or read_json(path) != request:
        return "action=build builder=repair_context action_arg=prepare"
    if manifest.get("repair_context") != {
        "path": path.relative_to(root).as_posix(), "sha256": sha256_file(path),
        "sequence": request["sequence"],
    }:
        return "action=build builder=repair_context action_arg=prepare"
    return (
        f"action=delegate agent={PROFILE_AGENTS[request['profile']]} "
        f"profile={request['profile']} task=repair context=isolated "
        f"request={path.relative_to(root).as_posix()}"
    )


def next_agent_action(root: Path, task: str, experiment_id: str) -> str:
    if task == "planning":
        return _planning_action(root, experiment_id)
    if task == "implementation":
        return _implementation_action(root, experiment_id)
    if task == "plan-audit":
        return _plan_audit_action(root, experiment_id)
    if task == "implementation-audit":
        return _implementation_audit_action(root, experiment_id)
    if task == "integrity-audit":
        return _integrity_audit_action(root, experiment_id)
    if task == "evaluation":
        return _evaluation_action(root, experiment_id)
    if task == "repair":
        return _repair_action(root, experiment_id)
    raise ValueError(f"unknown agent task: {task}")


def _execute() -> str:
    parser = QuietArgumentParser(description="Resolve work before an agent starts.")
    parser.add_argument("--task", required=True, choices=sorted(TASKS))
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    return next_agent_action(root_from_script(), args.task, args.experiment_id)


if __name__ == "__main__":
    raise SystemExit(run_script("next-agent-action", _execute))
