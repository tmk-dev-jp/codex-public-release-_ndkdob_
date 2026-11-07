from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dl_research.config import load_config
from dl_research.experiment.comparison import require_comparison_budget
from scripts.build_context import build_context
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.implementation_delta import lock_implementation_delta
from scripts.records import (
    field,
    plan_hash,
    section,
    validate_plan,
    validate_record_word_limits,
)
from scripts.scope import validate_scope
from scripts.workflow import experiment_manifest_path, require_active, set_phase


def lock_plan(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"DRAFT"})
    active = root / "experiments/active" / experiment_id
    record_path = active / "EXPERIMENT.md"
    scope_path = active / "SCOPE.json"
    config_path = root / manifest["config"]

    text = record_path.read_text(encoding="utf-8")
    validate_plan(text, stage=manifest.get("stage"))
    validate_record_word_limits(
        text,
        maximum_plan_words=int(
            state["budgets"].get("max_experiment_plan_words", 700)
        ),
    )
    config = load_config(config_path)
    require_comparison_budget(read_json(config_path), state)
    if config.experiment.id != experiment_id:
        raise ValueError("config experiment ID does not match")
    if config.experiment.stage != manifest.get("stage"):
        raise ValueError("config stage does not match experiment manifest")
    hypothesis = section(text, "## Hypothesis")
    if field(hypothesis, "Decision mode").lower() != config.decision.mode:
        raise ValueError("record Decision mode does not match config decision.mode")
    independent = set(state.get("review_policy", {}).get("independent_stages", []))
    if config.experiment.stage in independent and config.experiment.review_mode != "independent":
        raise ValueError(f"{config.experiment.stage} experiments require independent review")

    scope, scope_files = validate_scope(
        root,
        read_json(scope_path),
        maximum_files=int(state["budgets"].get("max_scope_files", 10)),
        maximum_planning_python_reads=int(
            state["budgets"].get("max_planning_python_reads", 3)
        ),
        maximum_implementation_entry_python_reads=int(
            state["budgets"].get("max_implementation_entry_python_reads", 3)
        ),
    )
    atomic_write_json(scope_path, scope)
    _, delta_metadata = lock_implementation_delta(
        root,
        experiment_id,
        text,
        scope,
        manifest["config"],
    )

    manifest["plan_sha256"] = plan_hash(record_path, config_path, scope_path)
    manifest["locked_config_sha256"] = sha256_file(config_path)
    manifest["scope_files"] = scope_files
    manifest["implementation_delta"] = delta_metadata
    manifest["plan_audit"] = None
    manifest["plan_review"] = {"status": "pending"}
    manifest["decision_facts"] = None
    (active / "DECISION_FACTS.json").unlink(missing_ok=True)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    set_phase(
        root,
        experiment_id,
        "PLANNED",
        objective="Audit the locked plan for metric gaming before human review.",
        review_required=False,
    )
    state_path = root / "research/STATE.json"
    state = read_json(state_path)
    state.setdefault("approvals", {})["plan_review_experiment_id"] = None
    state["next_action"] = {
        "mode": "audit_experiment_plan",
        "queue_id": manifest.get("queue_id"),
        "objective": "Audit the locked plan for metric gaming before human review.",
    }
    atomic_write_json(state_path, state)

    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    for item in index.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = "PLANNED"
    atomic_write_json(index_path, index)
    build_context(root)
    return active


def _execute() -> str:
    parser = QuietArgumentParser(description="Validate and lock one experiment plan.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return lock_plan(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("lock-plan", _execute))
