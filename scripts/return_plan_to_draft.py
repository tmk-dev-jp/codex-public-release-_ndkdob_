from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.common import QuietArgumentParser, atomic_write_json, read_json, root_from_script, run_script
from scripts.workflow import experiment_manifest_path, require_active


def return_plan_to_draft(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"PLANNED"})
    state["phase"] = "DRAFT"
    state["review_required"] = False
    state.setdefault("approvals", {})["plan_review_experiment_id"] = None
    state["next_action"] = {
        "mode": "revise_experiment_plan",
        "queue_id": manifest.get("queue_id"),
        "objective": "Revise the experiment plan in DRAFT, then lock it again.",
    }
    manifest["phase"] = "DRAFT"
    manifest["plan_sha256"] = None
    manifest["locked_config_sha256"] = None
    manifest["scope_files"] = []
    manifest["implementation_delta"] = None
    manifest["plan_audit"] = None
    manifest["plan_review"] = {"status": "revision_requested"}
    manifest["decision_facts"] = None
    (root / "experiments/active" / experiment_id / "DECISION_FACTS.json").unlink(
        missing_ok=True
    )
    (root / "experiments/active" / experiment_id / "PLAN_AUDIT.md").unlink(
        missing_ok=True
    )
    (
        root
        / "experiments/active"
        / experiment_id
        / "IMPLEMENTATION_DELTA.json"
    ).unlink(missing_ok=True)
    atomic_write_json(root / "research/STATE.json", state)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)

    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    for item in index.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = "DRAFT"
    atomic_write_json(index_path, index)
    build_context(root)
    return experiment_manifest_path(root, experiment_id)


def _execute() -> str:
    parser = QuietArgumentParser(description="Return a locked experiment plan to DRAFT for revision.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return return_plan_to_draft(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("return-plan-to-draft", _execute))
