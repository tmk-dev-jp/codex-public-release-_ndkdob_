from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dl_research.config import load_config
from scripts.build_context import build_context
from scripts.build_decision_facts import (
    require_current_decision_facts,
    require_record_decision_status,
)
from scripts.build_digest import build_digest
from scripts.build_implementation_review_bundle import (
    require_accepted_implementation_audit,
)
from scripts.build_plan_review_bundle import (
    require_accepted_plan_audit,
)
from scripts.build_review_bundle import require_accepted_integrity_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
    sha256_path_set,
)
from scripts.records import (
    plan_hash,
    validate_conclusion,
    validate_record_word_limits,
)
from scripts.workflow import require_active, set_phase


def finalize_experiment(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"READY_TO_FINALIZE"})
    active_dir = root / "experiments/active" / experiment_id
    completed_dir = root / "experiments/completed" / experiment_id
    if completed_dir.exists():
        raise FileExistsError(f"completed experiment already exists: {experiment_id}")

    record_path = active_dir / "EXPERIMENT.md"
    record_text = record_path.read_text(encoding="utf-8")
    validate_conclusion(record_text)
    validate_record_word_limits(
        record_text,
        maximum_plan_words=int(
            state["budgets"].get("max_experiment_plan_words", 700)
        ),
        maximum_conclusion_words=int(
            state["budgets"].get("max_experiment_conclusion_words", 400)
        ),
    )

    config_path = root / manifest["config"]
    config = load_config(config_path)
    if config.experiment.id != experiment_id:
        raise ValueError("config experiment ID does not match")
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    if plan_hash(
        record_path,
        config_path,
        active_dir / "SCOPE.json",
    ) != manifest.get("plan_sha256"):
        raise ValueError("Hypothesis, Method, config, or scope changed after plan locking")

    result_dir = root / manifest["result_dir"]
    metrics_path = result_dir / "metrics.json"
    runtime_manifest_path = result_dir / "manifest.json"
    if not metrics_path.is_file() or not runtime_manifest_path.is_file():
        raise FileNotFoundError("aggregate metrics or runtime manifest is missing")
    metrics = read_json(metrics_path)
    runtime_manifest = read_json(runtime_manifest_path)
    if metrics.get("experiment_id") != experiment_id:
        raise ValueError("metrics experiment ID does not match")
    if metrics.get("config_sha256") != manifest.get("locked_config_sha256"):
        raise ValueError("metrics were produced from a different config")
    current_implementation = sha256_path_set(root, manifest.get("implementation_files", []))
    if current_implementation != manifest.get("implementation_sha256"):
        raise ValueError("implementation changed after training")
    if runtime_manifest.get("implementation_sha256") != current_implementation:
        raise ValueError("runtime manifest implementation hash does not match")
    require_accepted_plan_audit(root, active_dir, manifest, allow_warn=True)
    require_accepted_implementation_audit(root, state, active_dir, manifest)
    facts = require_current_decision_facts(root, active_dir, manifest)
    require_record_decision_status(record_text, facts)

    if config.experiment.review_mode == "independent":
        require_accepted_integrity_audit(root, active_dir, manifest)
        evaluation = manifest.get("evaluation")
        if not isinstance(evaluation, dict) or not (active_dir / "EVALUATION.md").is_file():
            raise ValueError("independent evaluation has not been accepted")

    set_phase(
        root,
        experiment_id,
        "FINALIZED",
        objective="Select the next decision-relevant experiment.",
        review_required=False,
    )
    manifest = read_json(active_dir / "MANIFEST.json")
    manifest.update(
        {
            "status": "completed",
            "phase": "FINALIZED",
            "record": f"experiments/completed/{experiment_id}/EXPERIMENT.md",
        }
    )
    atomic_write_json(active_dir / "MANIFEST.json", manifest)
    active_dir.rename(completed_dir)

    bundle = root / "review/bundles" / experiment_id
    if bundle.exists():
        review_completed = root / "review/completed" / experiment_id
        if review_completed.exists():
            shutil.rmtree(review_completed)
        bundle.rename(review_completed)

    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    item = next(
        (entry for entry in index.get("experiments", []) if entry.get("id") == experiment_id),
        None,
    )
    if item is None:
        raise ValueError(f"experiment is missing from INDEX.json: {experiment_id}")
    item.update(
        {
            "status": "completed",
            "phase": "FINALIZED",
            "record": f"experiments/completed/{experiment_id}/EXPERIMENT.md",
            "metrics": f"artifacts/results/{experiment_id}/metrics.json",
        }
    )
    atomic_write_json(index_path, index)

    state = read_json(root / "research/STATE.json")
    state.update(
        {
            "project_status": "ready",
            "active_experiment": None,
            "phase": None,
            "stage": None,
            "review_required": False,
            "latest_completed_experiment": experiment_id,
            "next_action": {
                "mode": "maintain_memory",
                "queue_id": state.get("next_action", {}).get("queue_id"),
                "objective": "Record durable insights, dead ends, open questions, and the experiment ledger entry.",
            },
        }
    )
    if state.get("approvals", {}).get("full_training_experiment_id") == experiment_id:
        state["approvals"]["full_training_experiment_id"] = None
    if state.get("approvals", {}).get("plan_review_experiment_id") == experiment_id:
        state["approvals"]["plan_review_experiment_id"] = None
    atomic_write_json(root / "research/STATE.json", state)
    build_digest(root)
    build_context(root)
    return completed_dir


def _execute() -> str:
    parser = QuietArgumentParser(description="Finalize one reviewed or locally evaluated experiment.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return finalize_experiment(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("finalize-experiment", _execute))
