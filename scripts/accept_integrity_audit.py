from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.build_review_bundle import audit_input_hashes
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.compress_audit_material import material_action
from scripts.records import field, require_filled
from scripts.workflow import experiment_manifest_path, mark_failed, require_active

FIELDS = [
    "Verdict",
    "Result provenance",
    "Plan adherence",
    "Metric validity",
    "Data leakage and split risk",
    "Scope discipline",
    "Blocking issue",
    "Required action",
]


def bundle_hash(bundle: Path, excluded_names: set[str] | None = None) -> str:
    digest = hashlib.sha256()
    excluded = (
        excluded_names
        if excluded_names is not None
        else {"EVALUATION.md", "INTEGRITY_AUDIT.md"}
    )
    for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
        if path.name in excluded:
            continue
        relative = path.relative_to(bundle).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _update_index(root: Path, experiment_id: str, phase: str) -> None:
    path = root / "experiments/INDEX.json"
    payload = read_json(path)
    for item in payload.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = phase
    atomic_write_json(path, payload)


def accept_integrity_audit(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"REVIEW_REQUIRED"})
    bundle = root / "review/bundles" / experiment_id
    audit_path = bundle / "INTEGRITY_AUDIT.md"
    if not audit_path.is_file():
        raise FileNotFoundError("INTEGRITY_AUDIT.md is missing from the review bundle")
    text = audit_path.read_text(encoding="utf-8")
    for label in FIELDS:
        require_filled(field(text, label), label)
    if re.search(r"<[A-Za-z][^>\n]*>", text):
        raise ValueError("integrity audit still contains template placeholders")
    verdict = field(text, "Verdict").lower()
    if verdict not in {"pass", "warn", "fail"}:
        raise ValueError("Verdict must be pass, warn, or fail")
    if material_action(root, state, bundle, experiment_id, "integrity-audit"):
        raise ValueError("audit material exceeds its budget; use $compress-audit-material")

    active = root / "experiments/active" / experiment_id
    accepted_path = active / "INTEGRITY_AUDIT.md"
    atomic_write_text(accepted_path, text)
    manifest["integrity_audit"] = {
        "path": f"experiments/active/{experiment_id}/INTEGRITY_AUDIT.md",
        "verdict": verdict,
        "audit_sha256": sha256_file(accepted_path),
        "bundle_sha256": bundle_hash(bundle),
        "audited_inputs": audit_input_hashes(root, active, manifest),
    }
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)

    if verdict == "fail":
        mark_failed(
            root,
            experiment_id,
            "Repair the integrity failure without changing the locked claim or decision rule.",
        )
        _update_index(root, experiment_id, "FAILED")
    else:
        state["review_required"] = True
        state["next_action"] = {
            "mode": "review_required",
            "queue_id": manifest.get("queue_id"),
            "objective": "Map accepted aggregate evidence to the narrowest supported claim.",
        }
        atomic_write_json(root / "research/STATE.json", state)
    build_context(root)
    return accepted_path


def _execute() -> str:
    parser = QuietArgumentParser(description="Accept one independent experiment integrity audit.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return accept_integrity_audit(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("accept-integrity-audit", _execute))
