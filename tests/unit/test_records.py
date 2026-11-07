from __future__ import annotations

import pytest

from scripts.records import validate_conclusion, validate_plan


def _record(novelty: str) -> str:
    return f"""# EXP-TEST

## Hypothesis

- Research objective: determine whether the proposed method improves useful accuracy
- Study role: feasibility
- Claim: a measurable prediction
- Rationale: a mechanism
- Alternative explanation: the gain comes from extra capacity
- Minimum discriminating evidence: matched-capacity baseline comparison
- Falsifier: a rejecting result
- Primary metric: accuracy maximize
- Diagnostic guardrail: none
- Baseline: BASE-TEST
- Decision mode: threshold
- Minimum meaningful effect: +0.01
- Expected trend: not_applicable
- Trend evidence rule: not_applicable
- Novelty check: {novelty}
- Hypothesis policy check: does not violate the configured hard bans
- Promotion rule: promote on threshold

## Method

- Evidence coverage: readiness now; matched baseline pilot and representative full evaluation before adoption
- Scale justification: two batches check execution only; research support needs the later comparisons
- Implementation: one core hypothesis-driven change
- Baseline behavior: the baseline returns the current representation
- Candidate behavior: the candidate applies one representation change
- Intervention point: src/model.py transform
- Unchanged invariants: data split metric seed and training budget
- Implementation profile: balanced
- Profile rationale: stable contracts and two scoped paths
- Data control: fixed split and preprocessing
- Training: smoke, seed 17, best checkpoint, bounded budget
- Evaluation: compare to baseline with the decision rule

## Conclusion

- Decision: pending
- Mechanical rule status: pending
- Decision-rule assessment: pending
- Primary result: pending
- Baseline comparison: pending
- Confidence and caveats: pending

## Issues and Next Direction

- Main issue: pending
- Next action: pending
- Stop condition: pending
"""


def test_validate_plan_requires_filled_novelty_check() -> None:
    with pytest.raises(ValueError, match="Novelty check"):
        validate_plan(_record("pending"))


def test_validate_plan_accepts_novelty_check() -> None:
    validate_plan(
        _record("tests a new mechanism beyond the registered baseline behavior")
    )


@pytest.mark.parametrize("label", [
    "Research objective", "Study role", "Evidence coverage", "Scale justification",
])
@pytest.mark.parametrize("value", [None, "pending"])
def test_validate_plan_requires_research_scale_fields(label: str, value: str | None) -> None:
    lines = _record("novel mechanism").splitlines()
    text = "\n".join(
        line if not line.startswith(f"- {label}:") else (
            "" if value is None else f"- {label}: {value}"
        )
        for line in lines
    )
    with pytest.raises(ValueError, match=label):
        validate_plan(text)


@pytest.mark.parametrize("role", ["core", "mechanism", "robustness", "tiny"])
def test_validate_plan_rejects_non_feasibility_smoke(role: str) -> None:
    text = _record("novel mechanism").replace("Study role: feasibility", f"Study role: {role}")
    with pytest.raises(ValueError, match="Study role"):
        validate_plan(text, stage="smoke")


@pytest.mark.parametrize("stage", ["pilot", "full"])
@pytest.mark.parametrize("role", ["feasibility", "core", "mechanism", "robustness"])
def test_validate_plan_allows_goal_sized_comparison(stage: str, role: str) -> None:
    text = _record("novel mechanism").replace("Study role: feasibility", f"Study role: {role}")
    text = text.replace(
        "one core hypothesis-driven change",
        "joint encoder and adapter required for one method; compare as a whole",
    )
    validate_plan(text, stage=stage)


def test_validate_plan_requires_explicit_baseline_behavior() -> None:
    text = _record("novel mechanism").replace(
        "- Baseline behavior: the baseline returns the current representation",
        "- Baseline behavior: pending",
    )

    with pytest.raises(ValueError, match="Baseline behavior"):
        validate_plan(text)


def test_validate_plan_rejects_unknown_implementation_profile() -> None:
    text = _record("novel mechanism").replace(
        "- Implementation profile: balanced",
        "- Implementation profile: cheap",
    )
    with pytest.raises(ValueError, match="Implementation profile"):
        validate_plan(text)


def test_validate_plan_rejects_guardrail_used_for_promotion() -> None:
    text = _record("novel mechanism").replace(
        "- Diagnostic guardrail: none",
        "- Diagnostic guardrail: choose whichever secondary metric improves",
    )
    with pytest.raises(ValueError, match="Diagnostic guardrail"):
        validate_plan(text)


def test_validate_plan_requires_minimum_discriminating_evidence() -> None:
    text = _record("novel mechanism").replace(
        "- Minimum discriminating evidence: matched-capacity baseline comparison",
        "- Minimum discriminating evidence: pending",
    )
    with pytest.raises(ValueError, match="Minimum discriminating evidence"):
        validate_plan(text)


def test_validate_plan_accepts_preregistered_trend_rule() -> None:
    text = _record("novel mechanism").replace(
        "- Decision mode: threshold\n"
        "- Minimum meaningful effect: +0.01\n"
        "- Expected trend: not_applicable\n"
        "- Trend evidence rule: not_applicable",
        "- Decision mode: trend\n"
        "- Minimum meaningful effect: not_applicable\n"
        "- Expected trend: accuracy rises as context coverage increases\n"
        "- Trend evidence rule: same direction in three locked coverage levels; mixed or reversed is conflicting",
    )
    validate_plan(text)


def test_validate_plan_rejects_trend_without_evidence_rule() -> None:
    text = _record("novel mechanism").replace(
        "- Decision mode: threshold\n"
        "- Minimum meaningful effect: +0.01\n"
        "- Expected trend: not_applicable\n"
        "- Trend evidence rule: not_applicable",
        "- Decision mode: trend\n"
        "- Minimum meaningful effect: not_applicable\n"
        "- Expected trend: accuracy rises with coverage\n"
        "- Trend evidence rule: not_applicable",
    )
    with pytest.raises(ValueError, match="Trend evidence rule"):
        validate_plan(text)


def test_validate_conclusion_requires_claim_scope() -> None:
    pending = (
        "- Decision: pending\n"
        "- Mechanical rule status: pending\n"
        "- Decision-rule assessment: pending\n"
        "- Primary result: pending\n"
        "- Baseline comparison: pending\n"
        "- Confidence and caveats: pending"
    )
    text = _record("novel mechanism").replace(
        pending,
        "- Decision: support\n"
        "- Mechanical rule status: met\n"
        "- Decision-rule assessment: locked threshold was met\n"
        "- Primary result: accuracy improved by 0.02\n"
        "- Baseline comparison: exceeded the locked threshold\n"
        "- Supported scope: this dataset, split, and seed\n"
        "- Unsupported or missing evidence: other datasets and seeds\n"
        "- Confidence and caveats: pilot evidence only",
    ).replace(
        "- Main issue: pending\n- Next action: pending\n- Stop condition: pending",
        "- Main issue: robustness remains unknown\n"
        "- Next action: run the preregistered robustness test\n"
        "- Stop condition: stop if the effect reverses",
    )
    validate_conclusion(text)
