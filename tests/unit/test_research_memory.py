from __future__ import annotations

from pathlib import Path

import pytest

from scripts.research_memory import (
    IDEA_KEYS,
    append_jsonl,
    read_jsonl,
    require_keys,
    validate_idea_bank,
    validate_jsonl_schema,
    validate_novelty_checks,
)


def _novelty(experiment_id: str = "EXP-TEST") -> dict:
    return {
        "experiment_id": experiment_id, "idea_id": "IDEA-TEST",
        "query_terms": ["synthetic mechanism under shift"],
        "similar_items": [
            {"source": "REF-A", "shared": "same representation", "difference": "fixed gate"},
            {"source": "REF-B", "shared": "same shift", "difference": "no adaptive gate"},
        ],
        "facet_comparison": {
            "mechanism": "adaptive rather than fixed gate",
            "condition": "same shift conditions",
            "data_regime": "same data budget",
            "objective": "same held-out task",
            "implementation_change": "one gate rule changes",
        },
        "novelty_claim": "adaptive gating predicts a specific response under shift",
        "risk": "low", "decision": "proceed", "human_review_needed": False,
    }


def test_novelty_requires_comparisons_not_just_a_proceed_label(tmp_path: Path) -> None:
    path = tmp_path / "novelty.jsonl"
    append_jsonl(path, _novelty())
    assert validate_novelty_checks(path) == []


@pytest.mark.parametrize("key,value", [
    ("human_review_needed", "false"), ("human_review_needed", None),
    ("query_terms", []), ("novelty_claim", "pending"), ("facet_comparison", {}),
    ("similar_items", []), ("similar_items", ["REF-A", "REF-B"]),
    ("similar_items", [{"source": "REF-A", "shared": "same", "difference": ""}] * 2),
    ("similar_items", [{"source": "REF-A", "shared": "same", "difference": "fixed"}] * 2),
])
def test_incomplete_novelty_cannot_proceed(tmp_path: Path, key: str, value: object) -> None:
    from scripts.next_autonomous_step import novelty_block_reason

    record = _novelty()
    record[key] = value
    path = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    append_jsonl(path, record)
    assert validate_novelty_checks(path)
    assert novelty_block_reason(tmp_path, "EXP-TEST") == "novelty-evidence-incomplete"


def test_insufficient_search_can_request_human_judgment(tmp_path: Path) -> None:
    path = tmp_path / "novelty.jsonl"
    record = _novelty()
    record.update(similar_items=[], decision="needs_human", human_review_needed=True)
    append_jsonl(path, record)
    assert validate_novelty_checks(path) == []


def test_jsonl_append_and_read_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    record = {
        "id": "IDEA-TEST",
        "status": "candidate",
        "hypothesis": "a compact hypothesis",
        "rationale": "a compact rationale",
        "novelty_axis": "mechanism",
        "mechanism": "a compact mechanism",
        "why_now": "a compact reason",
        "expected_failure_mode": "a compact failure mode",
        "minimal_test": "one compact test",
        "forbidden_by_policy": False,
        "source_refs": [],
        "next_test": "one smoke test",
    }

    append_jsonl(path, record)

    assert read_jsonl(path) == [record]
    assert validate_jsonl_schema(path, IDEA_KEYS, "idea") == []
    assert validate_idea_bank(path) == []


def test_require_keys_rejects_missing_fields() -> None:
    try:
        require_keys({"id": "IDEA-TEST"}, IDEA_KEYS, "idea")
    except ValueError as exc:
        assert "missing keys" in str(exc)
    else:
        raise AssertionError("missing keys were accepted")


def test_validate_idea_bank_rejects_invalid_axis(tmp_path: Path) -> None:
    path = tmp_path / "ideas.jsonl"
    append_jsonl(
        path,
        {
            "id": "IDEA-TEST",
            "status": "candidate",
            "hypothesis": "a compact hypothesis",
            "rationale": "a compact rationale",
            "novelty_axis": "unknown",
            "mechanism": "a compact mechanism",
            "why_now": "a compact reason",
            "expected_failure_mode": "a compact failure mode",
            "minimal_test": "one compact test",
            "forbidden_by_policy": False,
            "source_refs": [],
            "next_test": "one smoke test",
        },
    )

    assert "invalid novelty_axis" in "; ".join(validate_idea_bank(path))


def test_validate_novelty_checks_rejects_high_risk_proceed(tmp_path: Path) -> None:
    path = tmp_path / "novelty.jsonl"
    append_jsonl(
        path,
        {
            "experiment_id": "EXP-TEST",
            "idea_id": "IDEA-TEST",
            "query_terms": [],
            "similar_items": [],
            "facet_comparison": {},
            "novelty_claim": "compact claim",
            "risk": "high",
            "decision": "proceed",
            "human_review_needed": False,
        },
    )

    assert "high-risk novelty cannot proceed" in "; ".join(
        validate_novelty_checks(path)
    )
