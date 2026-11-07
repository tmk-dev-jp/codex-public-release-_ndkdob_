from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
)
from scripts.records import field
from scripts.research_memory import read_jsonl


def complete_memory_update(root: Path) -> str:
    state = read_json(root / "research/STATE.json")
    if state.get("active_experiment") is not None:
        raise ValueError("memory completion requires no active experiment")
    if state.get("next_action", {}).get("mode") != "maintain_memory":
        raise ValueError("next action is not maintain_memory")
    experiment_id = state.get("latest_completed_experiment")
    if not isinstance(experiment_id, str):
        raise ValueError("latest completed experiment is missing")
    ledger = read_jsonl(root / "experiments/LEDGER.jsonl")
    if not any(item.get("experiment_id") == experiment_id for item in ledger):
        raise ValueError(f"ledger entry is missing for {experiment_id}")
    evidence = read_jsonl(root / "research/EVIDENCE.jsonl")
    matching_evidence = [
        item for item in evidence if item.get("experiment_id") == experiment_id
    ]
    if not matching_evidence:
        raise ValueError(f"evidence entry is missing for {experiment_id}")
    evidence_id = matching_evidence[-1].get("id")
    if not isinstance(evidence_id, str):
        raise ValueError("evidence ID is missing")
    record_value = f"experiments/completed/{experiment_id}/EXPERIMENT.md"
    metrics_value = f"artifacts/results/{experiment_id}/metrics.json"
    record_path = root / record_value
    manifest_path = root / "experiments/completed" / experiment_id / "MANIFEST.json"
    if not record_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("completed record or manifest is missing")
    record = record_path.read_text(encoding="utf-8")
    evidence_record = matching_evidence[-1]
    expected_fields = {
        "decision": field(record, "Decision").lower(),
        "decision_rule_assessment": field(record, "Decision-rule assessment"),
        "primary_result": field(record, "Primary result"),
        "supported_scope": field(record, "Supported scope"),
        "unsupported_or_missing_evidence": field(
            record, "Unsupported or missing evidence"
        ),
        "record": record_value,
        "metrics": metrics_value,
    }
    for key, expected in expected_fields.items():
        if evidence_record.get(key) != expected:
            raise ValueError(f"evidence {key} does not match the finalized record")
    completed_manifest = read_json(manifest_path)
    audit = completed_manifest.get("integrity_audit")
    expected_integrity = audit.get("verdict") if isinstance(audit, dict) else "not_required"
    if evidence_record.get("integrity_verdict") != expected_integrity:
        raise ValueError("evidence integrity verdict does not match the manifest")
    claim_ids = evidence_record.get("claim_ids")
    active_claim_ids = set(state.get("active_claim_ids", []))
    if not isinstance(claim_ids, list) or not claim_ids or not set(claim_ids) <= active_claim_ids:
        raise ValueError("evidence claim IDs must be active claims")
    state["active_evidence_ids"] = list(
        dict.fromkeys([*state.get("active_evidence_ids", []), evidence_id])
    )
    queue_id = state.get("next_action", {}).get("queue_id")
    state["next_action"] = {
        "mode": "update_direction",
        "queue_id": queue_id,
        "objective": (
            "Update claims, proposed method, queue, and stop decision from durable memory."
        ),
    }
    atomic_write_json(root / "research/STATE.json", state)
    build_context(root)
    return experiment_id


def _execute() -> str:
    QuietArgumentParser(description="Advance after durable memory has been updated.").parse_args()
    return complete_memory_update(root_from_script())


if __name__ == "__main__":
    raise SystemExit(run_script("complete-memory-update", _execute))
