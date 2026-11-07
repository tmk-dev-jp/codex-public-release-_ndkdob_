from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.build_plan_review_bundle import require_accepted_plan_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.decision_integrity import _begin_acceptance, _is_accepting
from scripts.workflow import experiment_manifest_path, require_active

APPROVAL_SOURCES = {"human_review", "explicit_unattended_loop", "agent_research_decision"}


def approve_plan(
    root: Path, experiment_id: str, approval_source: str = "human_review", *,
    decision_path: Path | None = None,
) -> Path:
    if approval_source not in APPROVAL_SOURCES:
        raise ValueError(f"unsupported plan approval source: {approval_source}")
    state, manifest = require_active(root, experiment_id, {"PLANNED"})
    if state.get("next_action", {}).get("mode") != "review_experiment_plan":
        raise ValueError("plan audit and human review must precede approval")
    active = root / "experiments/active" / experiment_id
    if approval_source == "agent_research_decision":
        from scripts.research_decision import require_plan_decision

        if decision_path is None:
            raise ValueError("agent approval requires a current dispatched research decision")
        require_plan_decision(root, experiment_id, decision_path)
        if not _is_accepting(decision_path):
            from scripts.common import read_json
            from scripts.research_decision import accept_decision

            accept_decision(root, experiment_id, "plan", read_json(
                decision_path / "REQUEST.json",
            ).get("question", ""))
            return experiment_manifest_path(root, experiment_id)
    require_accepted_plan_audit(
        root,
        active,
        manifest,
        allow_warn=approval_source in {"human_review", "agent_research_decision"},
    )
    state.setdefault("approvals", {})["plan_review_experiment_id"] = experiment_id
    state["next_action"] = {
        "mode": "implement_experiment",
        "queue_id": manifest.get("queue_id"),
        "objective": "Implement only the approved locked plan and scoped tests.",
    }
    manifest["plan_review"] = {
        "status": "approved",
        "source": approval_source,
    }
    if decision_path is not None:
        manifest["plan_review"]["decision_path"] = decision_path.relative_to(root).as_posix()
        manifest["plan_review"]["decision_sha256"] = sha256_file(decision_path / "RESPONSE.json")
    if approval_source == "agent_research_decision":
        _begin_acceptance(root, decision_path)
    atomic_write_json(root / "research/STATE.json", state)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    build_context(root)
    return experiment_manifest_path(root, experiment_id)


def _execute() -> str:
    parser = QuietArgumentParser(description="Record approval for a locked experiment plan.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument(
        "--source",
        choices=sorted(APPROVAL_SOURCES),
        default="human_review",
        dest="approval_source",
    )
    args = parser.parse_args()
    root = root_from_script()
    return approve_plan(root, args.experiment_id, args.approval_source).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("approve-plan", _execute))
