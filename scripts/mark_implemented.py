from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.build_implementation_review_bundle import (
    implementation_review_required,
)
from scripts.build_plan_review_bundle import require_accepted_plan_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
    sha256_path_set,
)
from scripts.implementation_delta import complete_implementation_delta
from scripts.records import plan_hash
from scripts.tune_training_controls import tune_training_controls
from scripts.workflow import (
    comparison_results_recorded,
    experiment_manifest_path,
    require_active,
    set_phase,
)


def mark_implemented(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"PLANNED", "FAILED"})
    if state.get("phase") == "PLANNED" and state.get("approvals", {}).get(
        "plan_review_experiment_id"
    ) != experiment_id:
        raise ValueError("recorded plan approval is required before implementation")
    active = root / "experiments/active" / experiment_id
    if state.get("phase") == "PLANNED":
        require_accepted_plan_audit(
            root,
            active,
            manifest,
            allow_warn=True,
        )
    record_path = active / "EXPERIMENT.md"
    scope_path = active / "SCOPE.json"
    config_path = root / manifest["config"]
    result_dir = root / manifest["result_dir"]
    if plan_hash(record_path, config_path, scope_path) != manifest.get(
        "plan_sha256"
    ):
        raise ValueError("locked plan, config, or scope changed")
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    if comparison_results_recorded(root, manifest):
        raise ValueError(
            "comparison runs are recorded; do not erase them "
            "or mix repaired code with prior evidence"
        )
    if result_dir.exists():
        shutil.rmtree(result_dir)
    tune_training_controls(root, experiment_id)
    manifest = read_json(experiment_manifest_path(root, experiment_id))
    current_plan = plan_hash(record_path, config_path, scope_path)
    if current_plan != manifest.get("plan_sha256"):
        raise ValueError(
            "locked plan, config, or scope changed; create a new experiment "
            "or relock deliberately"
        )
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")

    scope = read_json(scope_path)
    _, delta_metadata = complete_implementation_delta(
        root,
        active,
        manifest,
        repair=state.get("phase") == "FAILED",
    )
    implementation_files = list(
        dict.fromkeys(scope.get("write_paths", []) + scope.get("test_paths", []))
    )
    implementation_hash = sha256_path_set(root, implementation_files)
    manifest["implementation_files"] = implementation_files
    manifest["implementation_sha256"] = implementation_hash
    manifest["implementation_delta"] = delta_metadata
    manifest["implementation_audit"] = None
    manifest["integrity_audit"] = None
    manifest["decision_facts"] = None
    manifest["evaluation"] = None
    (active / "DECISION_FACTS.json").unlink(missing_ok=True)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    requires_review = implementation_review_required(state, manifest)
    state, _ = set_phase(
        root,
        experiment_id,
        "IMPLEMENTED",
        objective=(
            "Audit the locked implementation before execution."
            if requires_review
            else "Run the deterministic sanity and training workflow."
        ),
        review_required=requires_review,
    )
    if requires_review:
        state["next_action"]["mode"] = "review_implementation"
        atomic_write_json(root / "research/STATE.json", state)

    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    for item in index.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = "IMPLEMENTED"
    atomic_write_json(index_path, index)
    build_context(root)
    return active


def _execute() -> str:
    parser = QuietArgumentParser(description="Record one completed scoped implementation.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return mark_implemented(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("mark-implemented", _execute))
