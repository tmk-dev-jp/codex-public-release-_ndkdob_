from __future__ import annotations

from pathlib import Path

import pytest
from test_plan_audit import EXPERIMENT_ID, _audit
from test_plan_audit import _root as audit_root
from test_records import _record
from test_research_memory import _novelty

from scripts.accept_evaluation import _evaluation_section
from scripts.accept_human_interpretation import _section as human_section
from scripts.accept_plan_audit import accept_plan_audit
from scripts.build_plan_review_bundle import build_plan_review_bundle
from scripts.common import read_json
from scripts.next_agent_action import next_agent_action
from scripts.next_unattended_loop_step import next_unattended_loop_step
from scripts.records import (
    field,
    normalize_record_format,
    plan_hash,
    plan_record_material,
    plan_word_count,
    replace_section,
    require_filled,
    section,
    validate_experiment_headings,
    validate_plan,
)
from scripts.research_memory import append_jsonl


def _formatted(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            line = "### 1. **" + line[3:].lower() + "**"
        elif line.startswith("- ") and ":" in line:
            label, value = line[2:].split(":", 1)
            line = f"  * **{label.lower()}** : **{value.strip()}**"
        lines.append(line)
    return "\r\n".join(lines) + "\r\n"


@pytest.mark.parametrize(
    "text",
    [
        "- Verdict: pass",
        "* **Verdict:** pass",
        "+ __Verdict__: __pass__",
        "1. **verdict** : **pass**",
        "VERDICT : pass",
        "- Verdict\uff1a pass",
    ],
)
def test_field_presentation_preserves_the_existing_value(text):
    assert field(text, "Verdict") == "pass"


def test_whole_plan_parses_without_rewriting_or_changing_word_budget():
    canonical = _record("tests a distinct representation mechanism")
    text = _formatted(canonical)
    validate_plan(text, stage="smoke")
    assert plan_word_count(text) == plan_word_count(canonical)
    assert field(section(text, "## Method"), "Implementation profile") == "balanced"
    normalized = normalize_record_format(text)
    assert normalize_record_format(normalized) == normalized
    assert "### 1." in text
    assert field(normalized, "Claim") == field(canonical, "Claim")


def test_missing_empty_and_duplicate_values_are_not_invented():
    with pytest.raises(ValueError, match="missing field"):
        field("- Required action: review", "Verdict")
    empty = field("- Verdict:\n- Required action: review\n", "Verdict")
    assert empty == ""
    with pytest.raises(ValueError, match="not filled"):
        require_filled(empty, "Verdict")
    with pytest.raises(ValueError, match="duplicate field"):
        field("- Verdict: pass\n* **Verdict:** fail\n", "Verdict")


def test_identical_repeated_values_do_not_require_a_new_decision():
    assert field("- Verdict: pass\n* **Verdict:** **pass**\n", "Verdict") == "pass"


@pytest.mark.parametrize("example", [
    "```markdown\n## Hypothesis\n- Verdict: pass\n```\n",
    "    ## Hypothesis\n    - Verdict: pass\n",
])
def test_code_examples_cannot_supply_fields_or_sections(example):
    record = _record("novel mechanism") + "\n" + example + "- Verdict: fail\n"
    validate_experiment_headings(record)
    assert field(record, "Verdict") == "fail"
    with pytest.raises(ValueError, match="missing field"):
        field(example, "Verdict")


def test_evaluation_and_human_sections_accept_formatting_without_copying_notes():
    text = _formatted(
        "## Conclusion\n- Decision: inconclusive\n\n"
        "## Issues and Next Direction\n- Stop recommendation: collect missing evidence\n"
    )
    conclusion = _evaluation_section(text, "## Conclusion", "## Issues and Next Direction")
    issues = _evaluation_section(text, "## Issues and Next Direction")
    assert field(conclusion, "Decision") == "inconclusive"
    assert "- Stop recommendation: collect missing evidence" in issues
    text += "### Japanese Notes\nHuman explanation.\n"
    human_issues = human_section(text, "## Issues and Next Direction", "## Japanese Notes")
    assert "Human explanation" not in human_issues


def test_existing_plan_hashes_and_locked_scientific_content_remain_protected(tmp_path):
    record = _record("novel mechanism")
    hypothesis = record.split("## Hypothesis", 1)[1].split("## Method", 1)[0].strip()
    method = record.split("## Method", 1)[1].split("## Conclusion", 1)[0].strip()
    assert plan_record_material(record) == (
        "## Hypothesis\n\n" + hypothesis + "\n\n## Method\n\n" + method + "\n"
    )
    path, config, scope = (tmp_path / name for name in ("record.md", "config.json", "scope.json"))
    path.write_text(record, encoding="utf-8")
    config.write_text("{}\n", encoding="utf-8")
    scope.write_text("{}\n", encoding="utf-8")
    digest = plan_hash(path, config, scope)
    completed = replace_section(record, "## Conclusion", "- Decision: inconclusive")
    path.write_text(completed, encoding="utf-8")
    assert plan_hash(path, config, scope) == digest
    path.write_text(completed.replace("+0.01", "+0.00"), encoding="utf-8")
    assert plan_hash(path, config, scope) != digest


def test_existing_formatted_audit_advances_unattended_loop_without_a_new_agent(tmp_path):
    active = audit_root(tmp_path)
    append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", _novelty(EXPERIMENT_ID))
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    output = _formatted(_audit())
    (bundle / "PLAN_AUDIT.md").write_text(output, encoding="utf-8")
    before = [(active / name).read_bytes() for name in ("EXPERIMENT.md", "SCOPE.json")]
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID) == (
        "action=accept acceptor=accept_plan_audit"
    )
    accept_plan_audit(tmp_path, EXPERIMENT_ID)
    result = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=approve-plan" in result
    assert field((active / "PLAN_AUDIT.md").read_text(encoding="utf-8"), "Verdict") == "pass"
    assert [(active / name).read_bytes() for name in ("EXPERIMENT.md", "SCOPE.json")] == before


def test_conflicting_audit_cannot_be_reformatted_into_approval(tmp_path):
    audit_root(tmp_path)
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    (bundle / "PLAN_AUDIT.md").write_text(
        _formatted(_audit()) + "- Verdict: fail\n", encoding="utf-8"
    )
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).startswith("action=blocked")
    with pytest.raises(ValueError, match="duplicate field"):
        accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert (
        read_json(tmp_path / "research/STATE.json")["next_action"]["mode"]
        == "audit_experiment_plan"
    )


def test_scientific_audit_failure_still_blocks_unattended_approval(tmp_path):
    audit_root(tmp_path)
    append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", _novelty(EXPERIMENT_ID))
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    (bundle / "PLAN_AUDIT.md").write_text(_formatted(_audit("fail")), encoding="utf-8")
    accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert next_unattended_loop_step(tmp_path, explicit_user_request=True).endswith(
        "reason=plan-audit-pass-required"
    )


def test_loop_skills_allow_presentation_recovery_and_retain_scientific_stops():
    root = Path(__file__).resolve().parents[2]
    for skill in ("run-one-unattended-loop", "run-autonomous-loop"):
        text = (root / ".agents/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "automation/PRESENTATION_REPAIR.md" in text
    policy = (root / "automation/PRESENTATION_REPAIR.md").read_text(encoding="utf-8")
    assert "never rerun training" in policy
    assert "missing research evidence" in policy
