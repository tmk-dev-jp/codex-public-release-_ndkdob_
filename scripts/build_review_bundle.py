from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dl_research.experiment.comparison_artifacts import comparison_input_hash
from scripts.build_decision_facts import (
    build_decision_facts,
    load_baseline_payload,
    require_current_decision_facts,
)
from scripts.build_plan_review_bundle import require_accepted_plan_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_file,
)
from scripts.implementation_delta import (
    DELTA_FILENAME,
    compact_implementation_delta,
    require_current_implementation_delta,
)
from scripts.workflow import require_active


class IntegrityAuditRequiredError(ValueError):
    pass


def audit_input_hashes(root: Path, active: Path, manifest: dict) -> dict[str, str | None]:
    require_current_implementation_delta(root, active, manifest)
    result_dir = root / manifest["result_dir"]
    return {
        "plan_sha256": manifest.get("plan_sha256"),
        "implementation_sha256": manifest.get("implementation_sha256"),
        "implementation_delta_sha256": sha256_file(active / DELTA_FILENAME),
        "config_sha256": sha256_file(root / manifest["config"]),
        "scope_sha256": sha256_file(active / "SCOPE.json"),
        "plan_audit_sha256": (
            sha256_file(active / "PLAN_AUDIT.md")
            if (active / "PLAN_AUDIT.md").is_file()
            else None
        ),
        "metrics_sha256": sha256_file(result_dir / "metrics.json"),
        "comparison_sha256": comparison_input_hash(root, root / manifest["config"]),
        "runtime_manifest_sha256": sha256_file(result_dir / "manifest.json"),
        "decision_facts_sha256": sha256_file(active / "DECISION_FACTS.json"),
        "implementation_audit_sha256": (
            sha256_file(active / "IMPLEMENTATION_AUDIT.md")
            if (active / "IMPLEMENTATION_AUDIT.md").is_file()
            else None
        ),
    }


def require_accepted_integrity_audit(
    root: Path,
    active: Path,
    manifest: dict,
) -> None:
    audit = manifest.get("integrity_audit")
    if not isinstance(audit, dict) or audit.get("verdict") not in {"pass", "warn"}:
        raise IntegrityAuditRequiredError(
            "accepted pass or warn integrity audit is required"
        )
    audit_path = active / "INTEGRITY_AUDIT.md"
    if not audit_path.is_file() or audit.get("audit_sha256") != sha256_file(
        audit_path
    ):
        raise IntegrityAuditRequiredError(
            "accepted integrity audit changed after acceptance"
        )
    try:
        current_inputs = audit_input_hashes(root, active, manifest)
    except (OSError, ValueError) as exc:
        raise IntegrityAuditRequiredError(
            "integrity audit inputs are unavailable"
        ) from exc
    if audit.get("audited_inputs") != current_inputs:
        raise IntegrityAuditRequiredError(
            "integrity-audited inputs changed after review"
        )


def build_review_bundle(root: Path, experiment_id: str) -> Path:
    build_decision_facts(root, experiment_id)
    state, manifest = require_active(
        root,
        experiment_id,
        {"TRAINED", "REVIEW_REQUIRED", "READY_TO_FINALIZE"},
    )
    active = root / "experiments/active" / experiment_id
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    delta = require_current_implementation_delta(root, active, manifest)
    require_current_decision_facts(root, active, manifest)
    result_dir = root / manifest["result_dir"]
    metrics_path = result_dir / "metrics.json"
    runtime_manifest_path = result_dir / "manifest.json"
    if not metrics_path.is_file() or not runtime_manifest_path.is_file():
        raise FileNotFoundError("aggregate metrics or runtime manifest is missing")

    bundle = root / "review/bundles" / experiment_id
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    atomic_write_text(bundle / "GOAL.md", (root / "research/GOAL.md").read_text(encoding="utf-8"))
    atomic_write_text(
        bundle / "PLAN_AUDIT.md",
        (active / "PLAN_AUDIT.md").read_text(encoding="utf-8"),
    )
    atomic_write_text(
        bundle / "EXPERIMENT.md",
        (active / "EXPERIMENT.md").read_text(encoding="utf-8"),
    )
    implementation_audit = active / "IMPLEMENTATION_AUDIT.md"
    if implementation_audit.is_file():
        atomic_write_text(
            bundle / "IMPLEMENTATION_AUDIT.md",
            implementation_audit.read_text(encoding="utf-8"),
        )
    atomic_write_json(bundle / "METRICS.json", read_json(metrics_path))
    atomic_write_json(
        bundle / "BASELINE.json",
        load_baseline_payload(root, manifest.get("baseline_id")),
    )
    atomic_write_json(
        bundle / "DECISION_FACTS.json",
        read_json(active / "DECISION_FACTS.json"),
    )
    atomic_write_json(bundle / "MANIFEST.json", read_json(runtime_manifest_path))
    scope = read_json(active / "SCOPE.json")
    atomic_write_json(bundle / "SCOPE.json", scope)
    atomic_write_json(
        bundle / DELTA_FILENAME,
        compact_implementation_delta(delta),
    )
    atomic_write_json(bundle / "CONFIG.json", read_json(root / manifest["config"]))
    snapshot_paths = []
    for value in manifest.get("implementation_files", []):
        source = safe_relative_path(root, str(value))
        target = bundle / "implementation" / Path(str(value))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        snapshot_paths.append(target.relative_to(bundle).as_posix())
    request = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "review_question": (
            "Does the evidence answer the research question and distinguish the claimed novelty "
            "from the alternative explanation, as well as meet the locked decision rule? "
            "Use research_focus in DECISION_FACTS.json; metric success alone is insufficient."
        ),
        "decision_facts": "DECISION_FACTS.json",
        "implementation_delta": DELTA_FILENAME,
        "implementation_snapshot": snapshot_paths,
        "instruction": (
            "Review only this closed bundle. Do not inspect repository files outside it."
        ),
        "state_review_required": bool(state.get("review_required")),
    }
    atomic_write_json(bundle / "REQUEST.json", request)
    integrity_request = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "review_question": (
            "Are results traceable, plan-adherent, metric-valid, leakage-aware, and scoped "
            "no broader than the executed experiment?"
        ),
        "verdicts": ["pass", "warn", "fail"],
        "decision_facts": "DECISION_FACTS.json",
        "implementation_delta": DELTA_FILENAME,
        "audited_input_hashes": audit_input_hashes(root, active, manifest),
    }
    atomic_write_json(bundle / "INTEGRITY_REQUEST.json", integrity_request)
    integrity_template = (root / "experiments/templates/INTEGRITY_AUDIT.md").read_text(
        encoding="utf-8"
    )
    atomic_write_text(
        bundle / "INTEGRITY_AUDIT.md",
        integrity_template.replace("{{EXPERIMENT_ID}}", experiment_id),
    )
    template = (root / "experiments/templates/EVALUATION.md").read_text(encoding="utf-8")
    atomic_write_text(
        bundle / "EVALUATION.md",
        template.replace("{{EXPERIMENT_ID}}", experiment_id),
    )
    return bundle


def _execute() -> str:
    parser = QuietArgumentParser(description="Build one compact experiment review bundle.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return build_review_bundle(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("build-review-bundle", _execute))
