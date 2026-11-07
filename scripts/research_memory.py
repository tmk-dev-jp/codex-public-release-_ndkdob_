from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.common import atomic_write_text

IDEA_KEYS = {
    "id",
    "status",
    "hypothesis",
    "rationale",
    "novelty_axis",
    "mechanism",
    "why_now",
    "expected_failure_mode",
    "minimal_test",
    "forbidden_by_policy",
    "source_refs",
    "next_test",
}
NOVELTY_KEYS = {
    "experiment_id",
    "idea_id",
    "query_terms",
    "similar_items",
    "facet_comparison",
    "novelty_claim",
    "risk",
    "decision",
    "human_review_needed",
}
LEDGER_KEYS = {
    "experiment_id",
    "stage",
    "core_change",
    "primary_metric",
    "decision",
    "decision_rule_assessment",
    "human_interpretation",
    "next_action",
}
EVIDENCE_KEYS = {
    "id",
    "experiment_id",
    "claim_ids",
    "decision",
    "decision_rule_assessment",
    "primary_result",
    "supported_scope",
    "unsupported_or_missing_evidence",
    "integrity_verdict",
    "record",
    "metrics",
}
NOVELTY_AXES = {
    "mechanism",
    "condition",
    "data_regime",
    "objective",
    "efficiency",
    "robustness",
    "failure_mode",
}
NOVELTY_RISKS = {"low", "medium", "high", "block"}
NOVELTY_DECISIONS = {"proceed", "revise", "reject", "needs_human"}
NOVELTY_CONTRACT_VERSION = "1.0"
CONTRIBUTION_KINDS = ("discovery", "method_advance", "boundary", "replication")
EVIDENCE_DECISIONS = {"support", "reject", "inconclusive"}
INTEGRITY_VERDICTS = {"pass", "warn", "not_required"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path} line {line_number} must be an object")
        records.append(value)
    return records


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    records = read_jsonl(path)
    records.append(record)
    payload = "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in records)
    atomic_write_text(path, payload)


def require_keys(record: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - set(record))
    if missing:
        raise ValueError(f"{label} record missing keys: {', '.join(missing)}")


def validate_jsonl_schema(path: Path, keys: set[str], label: str) -> list[str]:
    errors: list[str] = []
    try:
        records = read_jsonl(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"invalid {label}: {exc}"]
    for index, record in enumerate(records, 1):
        missing = sorted(keys - set(record))
        if missing:
            errors.append(f"{label} line {index} missing keys: {', '.join(missing)}")
    return errors


def validate_idea_bank(path: Path) -> list[str]:
    errors = validate_jsonl_schema(path, IDEA_KEYS, "idea")
    try:
        records = read_jsonl(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return errors
    for index, record in enumerate(records, 1):
        axis = record.get("novelty_axis")
        if axis not in NOVELTY_AXES:
            errors.append(f"idea line {index} invalid novelty_axis: {axis}")
        if not isinstance(record.get("forbidden_by_policy"), bool):
            errors.append(f"idea line {index} forbidden_by_policy must be boolean")
        if not isinstance(record.get("source_refs"), list):
            errors.append(f"idea line {index} source_refs must be a list")
    return errors


def validate_novelty_checks(path: Path) -> list[str]:
    errors = validate_jsonl_schema(path, NOVELTY_KEYS, "novelty")
    try:
        records = read_jsonl(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return errors
    for index, record in enumerate(records, 1):
        risk = record.get("risk")
        decision = record.get("decision")
        if not isinstance(risk, str) or risk not in NOVELTY_RISKS:
            errors.append(f"novelty line {index} invalid risk: {risk}")
        if not isinstance(decision, str) or decision not in NOVELTY_DECISIONS:
            errors.append(f"novelty line {index} invalid decision: {decision}")
        if not isinstance(record.get("query_terms"), list):
            errors.append(f"novelty line {index} query_terms must be a list")
        if not isinstance(record.get("similar_items"), list):
            errors.append(f"novelty line {index} similar_items must be a list")
        if not isinstance(record.get("facet_comparison"), dict):
            errors.append(f"novelty line {index} facet_comparison must be an object")
        if not isinstance(record.get("human_review_needed"), bool):
            errors.append(f"novelty line {index} human_review_needed must be boolean")
        if risk in ("high", "block") and decision == "proceed":
            errors.append(f"novelty line {index} high-risk novelty cannot proceed")
        if decision == "proceed":
            errors.extend(
                f"novelty line {index} {error}" for error in novelty_evidence_errors(record)
            )
        elif "contribution" in record:
            errors.extend(
                f"novelty line {index} {error}" for error in _contribution_errors(record)
            )
    return errors


def latest_novelty(root: Path, experiment_id: str) -> dict[str, Any] | None:
    records = read_jsonl(root / "research/novelty/NOVELTY_CHECKS.jsonl")
    return next(
        (item for item in reversed(records) if item.get("experiment_id") == experiment_id), None,
    )


def novelty_contract_required(manifest: object) -> bool:
    """An absent marker preserves legacy contracts; unknown versions fail closed."""
    if not isinstance(manifest, dict):
        raise ValueError("novelty contract requires a manifest object")
    if "novelty_contract_version" not in manifest:
        return False
    if manifest["novelty_contract_version"] != NOVELTY_CONTRACT_VERSION:
        raise ValueError("unsupported novelty_contract_version")
    return True


def _filled(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value.strip())
        and value.strip().lower() not in {"pending", "none", "n/a", "not_recorded"}
        and not value.strip().startswith("<")
    )


def _contribution_errors(record: dict[str, Any]) -> list[str]:
    contribution = record.get("contribution")
    if not isinstance(contribution, dict):
        return ["contribution must be an object"]
    errors = []
    if contribution.get("schema_version") != NOVELTY_CONTRACT_VERSION:
        errors.append("unsupported contribution schema_version")
    if contribution.get("kind") not in CONTRIBUTION_KINDS:
        errors.append("unsupported contribution kind")
    for key in (
        "inference", "advance", "alternative", "candidate_prediction",
        "alternative_prediction", "discriminating_test", "advance_criterion",
    ):
        if not _filled(contribution.get(key)):
            errors.append(f"contribution {key} must be substantive text")
    candidate = contribution.get("candidate_prediction")
    alternative = contribution.get("alternative_prediction")
    if isinstance(candidate, str) and isinstance(alternative, str) and (
        " ".join(candidate.split()).casefold() == " ".join(alternative.split()).casefold()
    ):
        errors.append("contribution predictions must differ")
    observations = contribution.get("source_observations")
    if not isinstance(observations, list) or not 1 <= len(observations) <= 3:
        errors.append("contribution requires 1-3 source_observations")
        return errors
    items = record.get("similar_items")
    sources = {
        item["source"] for item in items
        if isinstance(item, dict) and isinstance(item.get("source"), str)
    } if isinstance(items, list) else set()
    seen = set()
    for observation in observations:
        if not isinstance(observation, dict) or not all(
            _filled(observation.get(key)) for key in ("source", "observation")
        ):
            errors.append("contribution observation requires source and substantive observation")
            continue
        source = observation["source"]
        if source not in sources:
            errors.append("contribution source must exactly match a similar_items source")
        pair = (source, " ".join(observation["observation"].split()).casefold())
        if pair in seen:
            errors.append("contribution source_observations must be distinct")
        seen.add(pair)
    return errors


def novelty_evidence_errors(
    record: object, *, require_contribution: bool = False,
) -> list[str]:
    """Check evidence structure and cited identifiers, not scientific truth."""
    if not isinstance(record, dict):
        return ["novelty record must be an object"]

    errors = []
    if NOVELTY_KEYS - record.keys():
        errors.append("incomplete novelty record")
    if record.get("human_review_needed") is not False:
        errors.append("proceed requires human_review_needed=false")
    if not _filled(record.get("novelty_claim")):
        errors.append("novelty_claim must state the proposed contribution")
    queries = record.get("query_terms")
    if not isinstance(queries, list) or not queries or not all(map(_filled, queries)):
        errors.append("query_terms must name the bounded search")
    items = record.get("similar_items")
    if not isinstance(items, list) or not 2 <= len(items) <= 3:
        errors.append("similar_items requires 2-3 source comparisons; otherwise needs_human")
    elif any(
        not isinstance(item, dict)
        or not all(_filled(item.get(key)) for key in ("source", "shared", "difference"))
        for item in items
    ):
        errors.append("similar_items requires source, shared and difference for each item")
    elif len({item["source"].strip().casefold() for item in items}) != len(items):
        errors.append("similar_items sources must be distinct")
    facets = record.get("facet_comparison")
    if not isinstance(facets, dict) or not all(
        _filled(facets.get(key))
        for key in ("mechanism", "condition", "data_regime", "objective", "implementation_change")
    ):
        errors.append(
            "facet_comparison must compare mechanism, condition, data_regime, "
            "objective, implementation_change"
        )
    if require_contribution or "contribution" in record:
        errors.extend(_contribution_errors(record))
    return errors


def validate_evidence(path: Path) -> list[str]:
    errors = validate_jsonl_schema(path, EVIDENCE_KEYS, "evidence")
    try:
        records = read_jsonl(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return errors
    for index, record in enumerate(records, 1):
        if not isinstance(record.get("id"), str) or not str(record.get("id")).startswith("E-"):
            errors.append(f"evidence line {index} has invalid ID")
        if not isinstance(record.get("claim_ids"), list):
            errors.append(f"evidence line {index} claim_ids must be a list")
        if record.get("decision") not in EVIDENCE_DECISIONS:
            errors.append(f"evidence line {index} has invalid decision")
        if record.get("integrity_verdict") not in INTEGRITY_VERDICTS:
            errors.append(f"evidence line {index} has invalid integrity_verdict")
    return errors
