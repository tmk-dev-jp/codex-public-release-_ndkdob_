"""Compact Markdown record parsing helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

IMPLEMENTATION_PROFILES = {"mechanical", "balanced", "frontier"}
STUDY_ROLES = {"feasibility", "core", "mechanism", "robustness"}
EXPERIMENT_HEADINGS = [
    "## Hypothesis",
    "## Method",
    "## Conclusion",
    "## Issues and Next Direction",
]


def _record_lines(text: str):
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$", line)
        visible = fence is None and marker is None and not line.expandtabs(4).startswith("    ")
        if marker:
            token, suffix = marker.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not suffix.strip():
                fence = None
        yield offset, line, visible
        offset += len(line)


def _unbold(value: str) -> str:
    value = value.strip()
    for marker in ("**", "__"):
        if value.startswith(marker) and value.endswith(marker) and len(value) >= 4:
            return value[2:-2].strip()
    return value


def _heading(line: str) -> str | None:
    match = re.fullmatch(r"[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*", line.rstrip("\r\n"))
    if not match:
        return None
    title = _unbold(re.sub(r"^\d+[.)][ \t]+", "", _unbold(match[1])))
    for heading in (*EXPERIMENT_HEADINGS, "## Japanese Notes"):
        if " ".join(title.split()).casefold() == heading[3:].casefold():
            return heading
    return None


def _field_parts(line: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"[ \t]*(?:(?:[-*+]|\d+[.)])[ \t]+)?(?:"
        r"\*\*([A-Za-z][A-Za-z \t-]*?)[ \t]*[:\uff1a]\*\*|"
        r"__([A-Za-z][A-Za-z \t-]*?)[ \t]*[:\uff1a]__|"
        r"(?:\*\*|__)?([A-Za-z][A-Za-z \t-]*?)(?:\*\*|__)?[ \t]*[:\uff1a]"
        r")[ \t]*(.*?)[ \t]*",
        line.rstrip("\r\n"),
    )
    if match:
        label = next(value for value in match.groups()[:3] if value is not None)
        return " ".join(label.split()).capitalize(), _unbold(match[4])
    return None


def normalize_record_format(text: str) -> str:
    """Normalize presentation for parsing; never infer a missing fact or verdict."""
    lines = []
    for _, line, visible in _record_lines(text.lstrip("\ufeff")):
        value = line.rstrip("\r\n")
        if visible:
            heading, parts = _heading(value), _field_parts(value)
            if heading:
                value = heading
            elif parts:
                value = f"- {parts[0]}: {parts[1]}"
        lines.append(value)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def compact_record_format(text: str, labels: tuple[str, ...]) -> str:
    """Remove blank presentation and identical fields, never findings or code examples."""
    known = {label.casefold() for label in labels}
    seen = set()
    lines = []
    for _, line, visible in _record_lines(normalize_record_format(text)):
        if visible and not line.strip():
            continue
        parts = _field_parts(line) if visible else None
        if parts and parts[0].casefold() in known:
            if parts in seen:
                continue
            seen.add(parts)
        lines.append(line.rstrip("\r\n"))
    compact = "\n".join(lines) + "\n"
    for label in labels:
        if field(text, label) != field(compact, label):
            raise ValueError(f"compaction changed field: {label}")
    return compact


def record_extra_lines(text: str, labels: tuple[str, ...]) -> list[str]:
    known = {label.casefold() for label in labels}
    return [
        line.rstrip("\r\n")
        for _, line, visible in _record_lines(normalize_record_format(text))
        if line.strip()
        and not (visible and (parts := _field_parts(line)) and parts[0].casefold() in known)
    ]


def _heading_spans(text: str, heading: str) -> list[tuple[int, int]]:
    return [
        (offset, offset + len(line.rstrip("\r\n")))
        for offset, line, visible in _record_lines(text)
        if visible and _heading(line.lstrip("\ufeff") if offset == 0 else line) == heading
    ]


def _section_span(text: str, heading: str) -> tuple[int, int, int]:
    spans = _heading_spans(text, heading)
    if len(spans) != 1:
        raise ValueError(f"record must contain exactly one {heading}")
    begin, start = spans[0]
    following = [
        offset
        for other in EXPERIMENT_HEADINGS
        for offset, _ in _heading_spans(text, other)
        if offset > begin
    ]
    return begin, start, min(following) if following else len(text)


def section(text: str, heading: str, *, until: str | None = None) -> str:
    _, start, end = _section_span(text, heading)
    if until:
        following = _heading_spans(text, until)
        if len(following) != 1 or following[0][0] <= start:
            raise ValueError(f"record must contain exactly one following {until}")
        end = following[0][0]
    return text[start:end].strip()


def field(text: str, label: str) -> str:
    values = [
        parts[1]
        for _, line, visible in _record_lines(text)
        if visible and (parts := _field_parts(line)) and parts[0].casefold() == label.casefold()
    ]
    if not values:
        raise ValueError(f"missing field: {label}")
    if len(set(values)) != 1:
        raise ValueError(f"duplicate field: {label}")
    return values[0]


def require_filled(value: str, label: str) -> None:
    lowered = value.strip().lower()
    if not lowered or lowered == "pending" or lowered.startswith("<"):
        raise ValueError(f"field is not filled: {label}")


def research_focus(goal: str, record: str = "") -> dict[str, str]:
    """Project the existing question and plan fields; never infer a contribution."""
    question = re.search(r"^## Question\s*\n(.*?)(?=^## |\Z)", goal, re.M | re.S)
    focus = {"Research question": question[1].strip() if question else "not_recorded"}
    for label in (
        "Research objective", "Study role", "Novelty check", "Alternative explanation",
        "Minimum discriminating evidence", "Falsifier",
    ):
        try:
            focus[label] = field(record, label)
        except ValueError as exc:
            if str(exc) != f"missing field: {label}":
                raise
            focus[label] = "not_recorded"
    return focus


def validate_experiment_headings(text: str) -> None:
    positions = []
    for heading in EXPERIMENT_HEADINGS:
        spans = _heading_spans(text, heading)
        if len(spans) != 1:
            raise ValueError(f"record must contain exactly one {heading}")
        positions.append(spans[0][0])
    if positions != sorted(positions):
        raise ValueError(
            "experiment sections must follow Hypothesis, Method, Conclusion, Issues order"
        )


def _combined_section_word_count(text: str, headings: tuple[str, ...]) -> int:
    validate_experiment_headings(text)
    return len("\n".join(normalize_record_format(section(text, h)) for h in headings).split())


def plan_word_count(text: str) -> int:
    return _combined_section_word_count(text, ("## Hypothesis", "## Method"))


def conclusion_word_count(text: str) -> int:
    return _combined_section_word_count(text, ("## Conclusion", "## Issues and Next Direction"))


def validate_record_word_limits(
    text: str,
    *,
    maximum_plan_words: int | None = None,
    maximum_conclusion_words: int | None = None,
) -> None:
    if maximum_plan_words is not None:
        count = plan_word_count(text)
        if count > maximum_plan_words:
            raise ValueError(f"Hypothesis + Method exceeds {maximum_plan_words} words: {count}")
    if maximum_conclusion_words is not None:
        count = conclusion_word_count(text)
        if count > maximum_conclusion_words:
            raise ValueError(
                f"Conclusion + Issues exceeds {maximum_conclusion_words} words: {count}"
            )


def validate_plan(text: str, *, stage: str | None = None) -> None:
    validate_experiment_headings(text)
    plan_text = section(text, "## Hypothesis") + "\n" + section(text, "## Method")
    if re.search(r"<[A-Za-z][^>\n]*>", plan_text):
        raise ValueError("Hypothesis or Method still contains template placeholders")
    required = [
        "Research objective",
        "Study role",
        "Evidence coverage",
        "Scale justification",
        "Claim",
        "Rationale",
        "Alternative explanation",
        "Minimum discriminating evidence",
        "Falsifier",
        "Primary metric",
        "Diagnostic guardrail",
        "Baseline",
        "Decision mode",
        "Minimum meaningful effect",
        "Expected trend",
        "Trend evidence rule",
        "Novelty check",
        "Hypothesis policy check",
        "Promotion rule",
        "Implementation",
        "Baseline behavior",
        "Candidate behavior",
        "Intervention point",
        "Unchanged invariants",
        "Implementation profile",
        "Profile rationale",
        "Data control",
        "Training",
        "Evaluation",
    ]
    for label in required:
        require_filled(field(plan_text, label), label)
    role = field(plan_text, "Study role").lower()
    if role not in STUDY_ROLES:
        raise ValueError("Study role must be feasibility, core, mechanism, or robustness")
    if stage == "smoke" and role != "feasibility":
        raise ValueError(
            "smoke requires Study role feasibility; research evidence needs pilot or full"
        )
    profile = field(plan_text, "Implementation profile").lower()
    if profile not in IMPLEMENTATION_PROFILES:
        raise ValueError("Implementation profile must be mechanical, balanced, or frontier")
    guardrail = field(plan_text, "Diagnostic guardrail").lower()
    no_guardrail = {"n/a", "none", "not applicable", "not_applicable"}
    if guardrail not in no_guardrail and not any(
        marker in guardrail
        for marker in (
            "diagnostic only",
            "diagnostic-only",
            "not used for promotion",
            "non-promotion",
        )
    ):
        raise ValueError("Diagnostic guardrail must be none or explicitly non-promotion")
    mode = field(plan_text, "Decision mode").lower()
    if mode not in {"threshold", "trend"}:
        raise ValueError("Decision mode must be threshold or trend")
    not_applicable = {"n/a", "none", "not applicable", "not_applicable"}
    minimum_effect = field(plan_text, "Minimum meaningful effect").lower()
    expected_trend = field(plan_text, "Expected trend").lower()
    trend_rule = field(plan_text, "Trend evidence rule").lower()
    if mode == "threshold":
        if minimum_effect in not_applicable:
            raise ValueError("threshold mode requires Minimum meaningful effect")
        if expected_trend not in not_applicable or trend_rule not in not_applicable:
            raise ValueError("threshold mode requires trend fields to be not_applicable")
    else:
        if minimum_effect not in not_applicable:
            raise ValueError("trend mode requires Minimum meaningful effect to be not_applicable")
        if expected_trend in not_applicable or trend_rule in not_applicable:
            raise ValueError("trend mode requires Expected trend and Trend evidence rule")


def validate_conclusion(text: str) -> None:
    validate_experiment_headings(text)
    result_text = (
        section(text, "## Conclusion") + "\n" + section(text, "## Issues and Next Direction")
    )
    required = [
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
        "Stop condition",
    ]
    for label in required:
        require_filled(field(result_text, label), label)
    decision = field(result_text, "Decision").lower()
    if decision not in {"support", "reject", "inconclusive"}:
        raise ValueError("Decision must be support, reject, or inconclusive")


def plan_record_material(text: str) -> str:
    validate_experiment_headings(text)
    return (
        "## Hypothesis\n\n"
        + section(text, "## Hypothesis").strip()
        + "\n\n## Method\n\n"
        + section(text, "## Method").strip()
        + "\n"
    )


def plan_hash(record_path: Path, config_path: Path, scope_path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(plan_record_material(record_path.read_text(encoding="utf-8")).encode("utf-8"))
    digest.update(b"\0config\0")
    digest.update(config_path.read_bytes())
    digest.update(b"\0scope\0")
    digest.update(scope_path.read_bytes())
    return digest.hexdigest()


def replace_section(text: str, heading: str, body: str) -> str:
    validate_experiment_headings(text)
    begin, _, end = _section_span(text, heading)
    prefix = text[:begin].rstrip()
    suffix = text[end:].lstrip()
    result = (prefix + "\n\n" if prefix else "") + heading + "\n\n" + body.strip() + "\n\n"
    if suffix:
        result += suffix
    return result.rstrip() + "\n"
