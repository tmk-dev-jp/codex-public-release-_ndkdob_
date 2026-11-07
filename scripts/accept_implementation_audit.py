from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.accept_integrity_audit import bundle_hash
from scripts.build_context import build_context
from scripts.build_implementation_review_bundle import (
    implementation_audit_input_hashes,
    implementation_review_required,
)
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
    "Plan fidelity",
    "Data split and leakage",
    "Loss and optimization",
    "Metric implementation",
    "Reproducibility and checkpointing",
    "Scope and minimality",
    "Declared implementation delta",
    "Blocking issue",
    "Required action",
]


def _update_index(root: Path, experiment_id: str, phase: str) -> None:
    path = root / "experiments/INDEX.json"
    payload = read_json(path)
    for item in payload.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = phase
    atomic_write_json(path, payload)


def accept_implementation_audit(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"IMPLEMENTED"})
    if state.get("next_action", {}).get("mode") != "review_implementation":
        raise ValueError("next action is not review_implementation")
    if not implementation_review_required(state, manifest):
        raise ValueError("implementation review is not required for this stage")
    active = root / "experiments/active" / experiment_id
    bundle = root / "review/bundles" / experiment_id
    request_path = bundle / "IMPLEMENTATION_REQUEST.json"
    audit_path = bundle / "IMPLEMENTATION_AUDIT.md"
    if not request_path.is_file() or not audit_path.is_file():
        raise FileNotFoundError("implementation review bundle is incomplete")

    text = audit_path.read_text(encoding="utf-8")
    for label in FIELDS:
        require_filled(field(text, label), label)
    if re.search(r"<[A-Za-z][^>\n]*>", text):
        raise ValueError("implementation audit still contains template placeholders")
    verdict = field(text, "Verdict").lower()
    if verdict not in {"pass", "warn", "fail"}:
        raise ValueError("Verdict must be pass, warn, or fail")

    audited_inputs = implementation_audit_input_hashes(root, active, manifest)
    request = read_json(request_path)
    if request.get("audited_input_hashes") != audited_inputs:
        raise ValueError("implementation review inputs changed before acceptance")
    if material_action(root, state, bundle, experiment_id, "implementation-audit"):
        raise ValueError("audit material exceeds its budget; use $compress-audit-material")

    accepted_path = active / "IMPLEMENTATION_AUDIT.md"
    atomic_write_text(accepted_path, text)
    manifest["implementation_audit"] = {
        "path": (
            f"experiments/active/{experiment_id}/IMPLEMENTATION_AUDIT.md"
        ),
        "verdict": verdict,
        "audit_sha256": sha256_file(accepted_path),
        "bundle_sha256": bundle_hash(bundle, {"IMPLEMENTATION_AUDIT.md"}),
        "audited_inputs": audited_inputs,
    }
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)

    if verdict == "fail":
        mark_failed(
            root,
            experiment_id,
            "Repair the rejected implementation audit without changing the locked plan.",
        )
        _update_index(root, experiment_id, "FAILED")
    else:
        state["review_required"] = False
        state["next_action"] = {
            "mode": "implemented",
            "queue_id": manifest.get("queue_id"),
            "objective": "Run the deterministic sanity and training workflow.",
        }
        atomic_write_json(root / "research/STATE.json", state)
    build_context(root)
    return accepted_path


def _execute() -> str:
    parser = QuietArgumentParser(description="Accept one implementation audit.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return accept_implementation_audit(
        root, args.experiment_id
    ).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("accept-implementation-audit", _execute))
