"""Lossless audit packing and guarded shortening of unaccepted audit reports."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
    sha256_file,
)
from scripts.records import (
    compact_record_format,
    field,
    normalize_record_format,
    record_extra_lines,
    require_filled,
)

AUDITS = {
    "plan-audit": ("PLAN_AUDIT_REQUEST.json", "PLAN_AUDIT.md", "plan_audit"),
    "implementation-audit": (
        "IMPLEMENTATION_REQUEST.json",
        "IMPLEMENTATION_AUDIT.md",
        "implementation_audit",
    ),
    "integrity-audit": ("INTEGRITY_REQUEST.json", "INTEGRITY_AUDIT.md", "integrity_audit"),
}
QUALIFIERS = re.compile(
    r"\b(?:not|no|never|only|unless|except|missing|unverified|insufficient|uncertain|"
    r"diagnostic|preliminary|inconclusive)\b",
    re.IGNORECASE,
)
FACTS = re.compile(
    r"`[^`]+`|(?<![\w.])[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?|"
    r"[\w.-]+(?:/[\w.-]+)+|<=|>=|!=|==|<|>"
)


def compact_json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def bounded_audit_request(request: dict, template: str, maximum: int) -> str:
    pretty = json.dumps(request, indent=2) + "\n"
    if len(pretty) + len(template) <= maximum:
        return pretty
    packed = compact_json_text(request)
    if len(packed) + len(template) > maximum:
        raise ValueError(
            f"plan audit bundle exceeds {maximum} characters even after lossless compression; "
            "essential content needs an explicit scope decision"
        )
    return packed


def _template(root: Path, experiment_id: str) -> str:
    return (
        (root / "experiments/templates/PLAN_AUDIT.md")
        .read_text(encoding="utf-8")
        .replace("{{EXPERIMENT_ID}}", experiment_id)
    )


def material_action(
    root: Path,
    state: dict,
    bundle: Path,
    experiment_id: str,
    task: str,
) -> str | None:
    budgets = state.get("budgets", {})
    request_name, report_name, _ = AUDITS[task]
    if task == "plan-audit":
        maximum = int(budgets.get("max_plan_audit_chars", 9000))
        request = bundle / request_name
        if len(request.read_text(encoding="utf-8")) + len(_template(root, experiment_id)) > maximum:
            return "action=compress skill=$compress-audit-material target=request"
    report = (bundle / report_name).read_text(encoding="utf-8")
    maximum_words = int(budgets.get("max_plan_audit_output_words", 250))
    if len(report) > int(budgets.get("max_context_chars", 9000)) or (
        task == "plan-audit" and len(normalize_record_format(report).split()) > maximum_words
    ):
        return "action=compress skill=$compress-audit-material target=report"
    return None


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON keys cannot be hidden by compression")
        result[key] = value
    return result


def _report_values(text: str, labels: tuple[str, ...]) -> dict[str, str]:
    values = {label: field(text, label) for label in labels}
    for label, value in values.items():
        require_filled(value, label)
    return values


def _validate_shortening(original: str, candidate: str, labels: tuple[str, ...]) -> None:
    before, after = _report_values(original, labels), _report_values(candidate, labels)
    if before["Verdict"] != after["Verdict"]:
        raise ValueError("compression must preserve the original verdict")
    for label in labels:
        before_words = set(re.findall(r"\b[\w-]+\b", before[label].casefold()))
        after_words = set(re.findall(r"\b[\w-]+\b", after[label].casefold()))
        if before_words != after_words:
            raise ValueError(f"compression must retain the field's unique vocabulary: {label}")
        for pattern in (FACTS, QUALIFIERS):
            if set(pattern.findall(before[label])) != set(pattern.findall(after[label])):
                raise ValueError(f"compression changed protected facts or qualifications: {label}")
    if record_extra_lines(original, labels) != record_extra_lines(candidate, labels):
        raise ValueError("preserve findings outside the required fields")


def compress_audit_material(root: Path, experiment_id: str, task: str, *, apply=False) -> str:
    # Import lazily: builders and the gate use the pure packing helpers above.
    from scripts.next_agent_action import TASK_FIELDS, next_agent_action

    action = next_agent_action(root, task, experiment_id)
    if not action.startswith(("action=compress ", "action=delegate ", "action=accept ")):
        raise ValueError("compression requires a current, otherwise valid audit bundle")
    request_name, report_name, manifest_key = AUDITS[task]
    state = read_json(root / "research/STATE.json")
    active = root / "experiments/active" / experiment_id
    if read_json(active / "MANIFEST.json").get(manifest_key):
        raise ValueError("accepted audits cannot be compressed")
    suffix = "-plan" if task == "plan-audit" else ""
    bundle = root / "review/bundles" / f"{experiment_id}{suffix}"
    labels = TASK_FIELDS[task]
    report_path = bundle / report_name
    text = report_path.read_text(encoding="utf-8")
    pending = any(field(text, label).lower() == "pending" for label in labels)
    compact_report = compact_record_format(text, labels)
    maximum_words = (
        int(state.get("budgets", {}).get("max_plan_audit_output_words", 250))
        if task == "plan-audit"
        else None
    )
    maximum_chars = int(state.get("budgets", {}).get("max_context_chars", 9000))
    archive = root / "review/compression" / experiment_id / task
    original_path, metadata_path = archive / "ORIGINAL.md", archive / "REQUEST.json"
    candidate_path = archive / "CANDIDATE.md"
    request = read_json(bundle / request_name)
    if apply:
        metadata = read_json(metadata_path)
        if metadata["source_sha256"] != sha256_file(original_path):
            raise ValueError("compression source changed")
        if metadata["source_sha256"] != sha256_file(report_path):
            raise ValueError("unaccepted report changed after compression preparation")
        if metadata["audited_input_hashes"] != request["audited_input_hashes"]:
            raise ValueError("compression inputs changed")
        candidate = candidate_path.read_text(encoding="utf-8")
        _validate_shortening(original_path.read_text(encoding="utf-8"), candidate, labels)
        if maximum_words and len(normalize_record_format(candidate).split()) > maximum_words:
            raise ValueError("compression candidate still exceeds the configured word budget")
        if len(candidate) > maximum_chars:
            raise ValueError("compression candidate still exceeds the context character budget")
        atomic_write_text(report_path, candidate)
        return f"{experiment_id} task={task} status=ready next=rerun-audit-gate"

    replacements = {}
    for path in sorted(bundle.glob("*.json")):
        if path.is_symlink():
            raise ValueError("redirected audit material cannot be compressed")
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        replacements[path] = compact_json_text(payload)
    if task == "plan-audit":
        maximum = int(state.get("budgets", {}).get("max_plan_audit_chars", 9000))
        if len(replacements[bundle / request_name]) + len(_template(root, experiment_id)) > maximum:
            return f"{experiment_id} status=blocked reason=essential-inputs-exceed-budget"
    for path, packed in replacements.items():
        if path.read_text(encoding="utf-8") != packed:
            atomic_write_text(path, packed)
    if compact_report != text:
        atomic_write_text(report_path, compact_report)
    if not pending and (
        len(compact_report) > maximum_chars
        or (maximum_words and len(compact_report.split()) > maximum_words)
    ):
        metadata = {
            "source_sha256": sha256_file(report_path),
            "audited_input_hashes": request["audited_input_hashes"],
        }
        if metadata_path.exists():
            if (
                read_json(metadata_path) != metadata
                or sha256_file(original_path) != metadata["source_sha256"]
            ):
                raise ValueError("compression source or inputs changed; preserve the original")
        else:
            atomic_write_text(original_path, compact_report)
            atomic_write_json(metadata_path, metadata)
        if not candidate_path.exists():
            atomic_write_text(candidate_path, compact_report)
        return (
            f"{experiment_id} task={task} status=needs-edit "
            f"candidate={candidate_path.relative_to(root).as_posix()}"
        )
    return f"{experiment_id} task={task} status=ready next=rerun-audit-gate"


def _execute() -> str:
    parser = QuietArgumentParser(description="Compress current unaccepted audit material.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--task", required=True, choices=sorted(AUDITS))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    return compress_audit_material(
        root_from_script(), args.experiment_id, args.task, apply=args.apply
    )


if __name__ == "__main__":
    raise SystemExit(run_script("compress-audit-material", _execute))
