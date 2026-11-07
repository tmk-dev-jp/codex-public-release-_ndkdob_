from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
    sha256_path_set,
)
from scripts.implementation_delta import (
    DELTA_FILENAME,
    compact_implementation_delta,
    require_current_implementation_delta,
)
from scripts.records import plan_hash
from scripts.workflow import require_active


class ImplementationAuditRequiredError(ValueError):
    pass


def implementation_review_required(state: dict, manifest: dict) -> bool:
    stages = set(state.get("review_policy", {}).get("independent_stages", []))
    stage = str(manifest.get("stage") or state.get("stage") or "")
    return stage in stages


def implementation_audit_input_hashes(
    root: Path,
    active: Path,
    manifest: dict,
) -> dict[str, str | None]:
    config_path = root / manifest["config"]
    require_current_implementation_delta(root, active, manifest)
    return {
        "plan_sha256": plan_hash(
            active / "EXPERIMENT.md", config_path, active / "SCOPE.json"
        ),
        "config_sha256": sha256_file(config_path),
        "scope_sha256": sha256_file(active / "SCOPE.json"),
        "plan_audit_sha256": (
            sha256_file(active / "PLAN_AUDIT.md")
            if (active / "PLAN_AUDIT.md").is_file()
            else None
        ),
        "implementation_sha256": sha256_path_set(
            root, manifest.get("implementation_files", [])
        ),
        "implementation_delta_sha256": sha256_file(active / DELTA_FILENAME),
    }


def require_accepted_implementation_audit(
    root: Path,
    state: dict,
    active: Path,
    manifest: dict,
) -> None:
    if not implementation_review_required(state, manifest):
        return
    audit = manifest.get("implementation_audit")
    if not isinstance(audit, dict) or audit.get("verdict") not in {"pass", "warn"}:
        raise ImplementationAuditRequiredError(
            "accepted implementation audit is required before pilot or full execution"
        )
    audit_path = active / "IMPLEMENTATION_AUDIT.md"
    if not audit_path.is_file() or audit.get("audit_sha256") != sha256_file(
        audit_path
    ):
        raise ImplementationAuditRequiredError(
            "accepted implementation audit changed after acceptance"
        )
    try:
        current_inputs = implementation_audit_input_hashes(root, active, manifest)
    except (OSError, ValueError) as exc:
        raise ImplementationAuditRequiredError(
            "implementation audit inputs are unavailable"
        ) from exc
    if audit.get("audited_inputs") != current_inputs:
        raise ImplementationAuditRequiredError(
            "implementation-audited inputs changed after review"
        )


def build_implementation_review_bundle(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"IMPLEMENTED"})
    if state.get("next_action", {}).get("mode") != "review_implementation":
        raise ValueError("next action is not review_implementation")
    if not implementation_review_required(state, manifest):
        raise ValueError("implementation review is not required for this stage")

    active = root / "experiments/active" / experiment_id
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    delta = require_current_implementation_delta(root, active, manifest)
    inputs = implementation_audit_input_hashes(root, active, manifest)
    config_path = root / manifest["config"]
    if inputs["config_sha256"] != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    if inputs["plan_sha256"] != manifest.get("plan_sha256"):
        raise ValueError("locked plan, config, or scope changed")
    if inputs["implementation_sha256"] != manifest.get("implementation_sha256"):
        raise ValueError("implementation changed after mark-implemented")

    bundle = root / "review/bundles" / experiment_id
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    atomic_write_text(
        bundle / "GOAL.md",
        (root / "research/GOAL.md").read_text(encoding="utf-8"),
    )
    atomic_write_text(
        bundle / "EXPERIMENT.md",
        (active / "EXPERIMENT.md").read_text(encoding="utf-8"),
    )
    atomic_write_text(
        bundle / "PLAN_AUDIT.md",
        (active / "PLAN_AUDIT.md").read_text(encoding="utf-8"),
    )
    atomic_write_json(bundle / "CONFIG.json", read_json(root / manifest["config"]))
    atomic_write_json(bundle / "SCOPE.json", read_json(active / "SCOPE.json"))
    atomic_write_json(bundle / "MANIFEST.json", manifest)
    atomic_write_json(
        bundle / DELTA_FILENAME,
        compact_implementation_delta(delta),
    )

    snapshot_paths = []
    for value in manifest.get("implementation_files", []):
        source = safe_relative_path(root, str(value))
        target = bundle / "implementation" / Path(str(value))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        snapshot_paths.append(target.relative_to(bundle).as_posix())

    atomic_write_json(
        bundle / "IMPLEMENTATION_REQUEST.json",
        {
            "schema_version": "1.0",
            "experiment_id": experiment_id,
            "review_question": (
                "Is the locked experiment implemented correctly and safely enough to run?"
            ),
            "verdicts": ["pass", "warn", "fail"],
            "implementation_snapshot": snapshot_paths,
            "implementation_delta": DELTA_FILENAME,
            "audited_input_hashes": inputs,
            "instruction": (
                "Review only this closed bundle. Open snapshot files one at a time as needed."
            ),
        },
    )
    template = (
        root / "experiments/templates/IMPLEMENTATION_AUDIT.md"
    ).read_text(encoding="utf-8")
    atomic_write_text(
        bundle / "IMPLEMENTATION_AUDIT.md",
        template.replace("{{EXPERIMENT_ID}}", experiment_id),
    )
    return bundle


def _execute() -> str:
    parser = QuietArgumentParser(description="Build one implementation review bundle.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return build_implementation_review_bundle(
        root, args.experiment_id
    ).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("build-implementation-review-bundle", _execute))
