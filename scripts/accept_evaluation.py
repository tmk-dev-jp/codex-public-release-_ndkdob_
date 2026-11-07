from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.build_decision_facts import require_current_decision_facts
from scripts.build_review_bundle import require_accepted_integrity_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
)
from scripts.records import field, normalize_record_format, replace_section, require_filled, section
from scripts.workflow import experiment_manifest_path, require_active, set_phase


def _evaluation_section(text: str, heading: str, next_heading: str | None = None) -> str:
    return section(normalize_record_format(text), heading, until=next_heading)


def accept_evaluation(root: Path, experiment_id: str) -> Path:
    _, manifest = require_active(root, experiment_id, {"REVIEW_REQUIRED"})
    active = root / "experiments/active" / experiment_id
    require_accepted_integrity_audit(root, active, manifest)
    facts = require_current_decision_facts(root, active, manifest)
    bundle = root / "review/bundles" / experiment_id
    evaluation_path = bundle / "EVALUATION.md"
    if not evaluation_path.is_file():
        raise FileNotFoundError("EVALUATION.md is missing from the review bundle")
    text = evaluation_path.read_text(encoding="utf-8")
    conclusion = _evaluation_section(text, "## Conclusion", "## Issues and Next Direction")
    issues = _evaluation_section(text, "## Issues and Next Direction")
    for label in [
        "Decision",
        "Mechanical rule status",
        "Decision-rule assessment",
        "Primary result",
        "Baseline comparison",
        "Supported scope",
        "Unsupported or missing evidence",
        "Confidence and caveats",
        "Main issue",
        "Next action",
        "Stop recommendation",
    ]:
        require_filled(field(text, label), label)
    decision = field(text, "Decision").lower()
    if decision not in {"support", "reject", "inconclusive"}:
        raise ValueError("Decision must be support, reject, or inconclusive")
    mechanical_status = field(text, "Mechanical rule status").lower()
    expected_status = str(facts["decision_rule"]["status"]).lower()
    if mechanical_status != expected_status:
        raise ValueError(
            f"Mechanical rule status must be {expected_status}; "
            f"found {mechanical_status}"
        )
    if re.search(r"<[A-Za-z][^>\n]*>", conclusion + "\n" + issues):
        raise ValueError("evaluation still contains template placeholders")

    record_path = active / "EXPERIMENT.md"
    record = record_path.read_text(encoding="utf-8")
    record = replace_section(record, "## Conclusion", conclusion)
    issues_for_record = issues.replace("- Stop recommendation:", "- Stop condition:")
    record = replace_section(record, "## Issues and Next Direction", issues_for_record)
    atomic_write_text(record_path, record)
    atomic_write_text(active / "EVALUATION.md", text)

    manifest["evaluation"] = {
        "path": f"experiments/active/{experiment_id}/EVALUATION.md",
        "decision": decision,
        "source_bundle": f"review/bundles/{experiment_id}",
    }
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    set_phase(
        root,
        experiment_id,
        "READY_TO_FINALIZE",
        objective="Validate and finalize the reviewed experiment.",
        review_required=False,
    )

    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    for item in index.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = "READY_TO_FINALIZE"
    atomic_write_json(index_path, index)
    build_context(root)
    return active / "EVALUATION.md"


def _execute() -> str:
    parser = QuietArgumentParser(
        description="Apply one independent evaluation to the active record."
    )
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return accept_evaluation(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("accept-evaluation", _execute))
