from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.accept_integrity_audit import bundle_hash
from scripts.build_context import build_context
from scripts.build_plan_review_bundle import plan_audit_input_hashes
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
from scripts.implementation_delta import require_locked_implementation_delta
from scripts.records import field, normalize_record_format, require_filled
from scripts.workflow import experiment_manifest_path, require_active

FIELDS = [
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
]


def accept_plan_audit(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"PLANNED"})
    if state.get("next_action", {}).get("mode") != "audit_experiment_plan":
        raise ValueError("next action is not audit_experiment_plan")

    active = root / "experiments/active" / experiment_id
    require_locked_implementation_delta(root, active, manifest)
    bundle = root / "review/bundles" / f"{experiment_id}-plan"
    request_path = bundle / "PLAN_AUDIT_REQUEST.json"
    audit_path = bundle / "PLAN_AUDIT.md"
    if not request_path.is_file() or not audit_path.is_file():
        raise FileNotFoundError("plan audit bundle is incomplete")

    text = audit_path.read_text(encoding="utf-8")
    for label in FIELDS:
        require_filled(field(text, label), label)
    if re.search(r"<[A-Za-z][^>\n]*>", text):
        raise ValueError("plan audit still contains template placeholders")
    verdict = field(text, "Verdict").lower()
    if verdict not in {"pass", "warn", "fail"}:
        raise ValueError("Verdict must be pass, warn, or fail")
    maximum_words = int(
        state["budgets"].get("max_plan_audit_output_words", 250)
    )
    word_count = len(normalize_record_format(text).split())
    if word_count > maximum_words:
        raise ValueError(
            f"plan audit exceeds {maximum_words} words: {word_count}"
        )

    audited_inputs = plan_audit_input_hashes(root, active, manifest)
    request = read_json(request_path)
    if request.get("audited_input_hashes") != audited_inputs:
        raise ValueError("plan audit inputs changed before acceptance")
    if material_action(root, state, bundle, experiment_id, "plan-audit"):
        raise ValueError("audit material exceeds its budget; use $compress-audit-material")

    accepted_path = active / "PLAN_AUDIT.md"
    atomic_write_text(accepted_path, text)
    manifest["plan_audit"] = {
        "path": f"experiments/active/{experiment_id}/PLAN_AUDIT.md",
        "verdict": verdict,
        "audit_sha256": sha256_file(accepted_path),
        "bundle_sha256": bundle_hash(bundle, {"PLAN_AUDIT.md"}),
        "audited_inputs": audited_inputs,
    }
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)

    state["next_action"] = {
        "mode": "review_experiment_plan",
        "queue_id": manifest.get("queue_id"),
        "objective": (
            "Review the locked plan and its blocking plan audit."
            if verdict == "fail"
            else "Review the locked plan and accepted plan audit for human approval."
        ),
    }
    atomic_write_json(root / "research/STATE.json", state)
    build_context(root)
    return accepted_path


def _execute() -> str:
    parser = QuietArgumentParser(description="Accept one plan audit.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return accept_plan_audit(
        root,
        args.experiment_id,
    ).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("accept-plan-audit", _execute))
