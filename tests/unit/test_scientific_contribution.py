from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from test_agent_led_loop import _respond, _setup
from test_plan_audit import EXPERIMENT_ID, REPO_ROOT, _accept, _root
from test_research_memory import _novelty

from scripts import new_experiment
from scripts.approve_plan import approve_plan
from scripts.build_plan_review_bundle import (
    PlanAuditRequiredError,
    build_plan_review_bundle,
    plan_audit_input_hashes,
    require_accepted_plan_audit,
)
from scripts.common import atomic_write_json, read_json
from scripts.next_autonomous_step import next_autonomous_step, novelty_block_reason
from scripts.research_decision import accept_decision, prepare_decision
from scripts.research_memory import (
    append_jsonl,
    latest_novelty,
    novelty_contract_required,
    novelty_evidence_errors,
    validate_novelty_checks,
)


def _contribution() -> dict:
    return {
        "schema_version": "1.0", "kind": "discovery",
        "source_observations": [
            {"source": "REF-A", "observation": "Fixed gating preserves nuisance features."},
        ],
        "inference": "Adaptive gating may suppress nuisance features under shift.",
        "advance": "Identify when gating controls shift sensitivity.",
        "alternative": "Additional inference compute explains the gain.",
        "candidate_prediction": "Shift accuracy improves at matched compute.",
        "alternative_prediction": "Matched compute removes the accuracy gain.",
        "discriminating_test": "Compare gates with identical data, seeds and compute.",
        "advance_criterion": "Meet the primary accuracy threshold; absent gains defeat the claim.",
    }


def _record() -> dict:
    return {**_novelty(EXPERIMENT_ID), "contribution": _contribution()}


def _mark(active: Path, value: object = "1.0") -> dict:
    manifest = read_json(active / "MANIFEST.json")
    manifest["novelty_contract_version"] = value
    atomic_write_json(active / "MANIFEST.json", manifest)
    return manifest


def _marked(root: Path) -> Path:
    active = _setup(root, verdict=None)
    _mark(active)
    append_jsonl(root / "research/novelty/NOVELTY_CHECKS.jsonl", _record())
    return active


def _compact_response() -> dict:
    # Synthetic source summaries exercise the complete response contract, not research truth.
    refs = ["https://example.org/fixed-gate", "https://example.org/adaptive-depth"]
    record = _record()
    record["similar_items"] = [
        {"source": refs[0], "shared": "gated representations", "difference": "fixed gating"},
        {"source": refs[1], "shared": "adaptive inference", "difference": "unmatched compute"},
    ]
    record["facet_comparison"] = {
        "mechanism": "adaptive gating", "condition": "held-out shift",
        "data_regime": "matched data", "objective": "shift accuracy",
        "implementation_change": "gate rule",
    }
    record["query_terms"] = ["adaptive gating shift compute"]
    record["novelty_claim"] = "Gating suppresses shift-sensitive nuisance features."
    observations = [
        {"source": refs[0], "observation": "Fixed gating preserves nuisance features."},
        {"source": refs[1], "observation": "Adaptive depth adds inference compute."},
    ]
    record["contribution"]["source_observations"] = deepcopy(observations)
    return {
        "action": "record_novelty",
        "rationale": "Matched compute distinguishes the competing explanations.",
        "evidence_refs": refs,
        "assessment": {
            "observations": observations,
            "counterargument": "Compute may explain improvement.",
            "uncertainty": "Source coverage remains bounded.",
            "change_condition": "Revise if matched-compute evidence already exists.",
        },
        "novelty": record,
    }


def test_new_experiments_opt_in(tmp_path, monkeypatch):
    for relative in (
        "configs/templates/smoke.json", "experiments/templates/EXPERIMENT.md",
        "experiments/templates/EXPERIMENT_AGENTS.md", "experiments/templates/SCOPE.json",
        "experiments/templates/MANIFEST.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, target)
    (tmp_path / "experiments/active").mkdir()
    atomic_write_json(tmp_path / "experiments/INDEX.json", {"experiments": []})
    atomic_write_json(
        tmp_path / "research/STATE.json", {"next_action": {"mode": "select_experiment"}},
    )
    monkeypatch.setattr(new_experiment, "build_context", lambda root: None)
    active = new_experiment.create_experiment(tmp_path, experiment_id="EXP-NEW", stage="smoke")
    assert read_json(active / "MANIFEST.json")["novelty_contract_version"] == "1.0"


@pytest.mark.parametrize("kind", ["discovery", "method_advance", "boundary", "replication"])
def test_contribution_kinds_are_structural_claims(kind):
    record = _record()
    record["contribution"]["kind"] = kind
    if kind == "replication":
        record["contribution"]["advance"] = "Reproducibility and supporting evidence only."
    assert novelty_evidence_errors(record, require_contribution=True) == []


@pytest.mark.parametrize("field,value", [
    ("schema_version", "2.0"), ("schema_version", []), ("kind", "routine_extension"),
    ("kind", {}), ("source_observations", []), ("source_observations", {}),
    ("source_observations", [None]),
    ("source_observations", [{"source": [], "observation": "Observed shift."}]),
    ("source_observations", [{"source": "REF-X", "observation": "Observed shift."}]),
    ("source_observations", [{"source": "ref-a", "observation": "Observed shift."}]),
    ("source_observations", [{"source": "REF-A ", "observation": "Observed shift."}]),
    ("source_observations", [{"source": "REF-A", "observation": "pending"}]),
    ("source_observations", [{"source": "REF-A", "observation": "Observed shift."}] * 2),
    ("source_observations", [{"source": "REF-A", "observation": "Observed shift."}] * 4),
    ("candidate_prediction", "  matched COMPUTE removes\n the accuracy gain.  "),
])
def test_invalid_contribution_fields_are_rejected(field, value):
    record = _record()
    record["contribution"][field] = value
    assert novelty_evidence_errors(record, require_contribution=True)


@pytest.mark.parametrize("field", [
    "inference", "advance", "alternative", "candidate_prediction",
    "alternative_prediction", "discriminating_test", "advance_criterion",
])
@pytest.mark.parametrize("value", [
    "", " pending ", "none", "n/a", "not_recorded", "<fill>", None, {},
])
def test_every_contribution_text_field_rejects_placeholders(field, value):
    record = _record()
    record["contribution"][field] = value
    assert novelty_evidence_errors(record, require_contribution=True)


@pytest.mark.parametrize("value", [None, [], "text", 1, {}])
def test_malformed_contribution_rejected_for_legacy_records_too(tmp_path, value):
    record = _novelty()
    record.update(contribution=value, decision="needs_human", human_review_needed=True)
    path = tmp_path / "novelty.jsonl"
    append_jsonl(path, record)
    assert validate_novelty_checks(path)
    assert novelty_evidence_errors(record)


def test_legacy_histories_hash_shape_and_accepted_audits_remain_usable(tmp_path):
    active = _root(tmp_path)
    path = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    append_jsonl(path, _novelty(EXPERIMENT_ID))
    before = path.read_bytes()
    manifest = _accept(tmp_path)
    assert not novelty_contract_required(manifest)
    assert "novelty_contract_sha256" not in manifest["plan_audit"]["audited_inputs"]
    require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=False)
    assert novelty_block_reason(tmp_path, EXPERIMENT_ID) is None
    assert validate_novelty_checks(path) == [] and path.read_bytes() == before


def test_marked_ordinary_route_and_bundle_require_contribution_without_writes(tmp_path):
    active = _setup(tmp_path, verdict=None)
    _mark(active)
    before = (tmp_path / "research/STATE.json").read_bytes()
    assert "novelty-evidence-incomplete" in next_autonomous_step(tmp_path)
    with pytest.raises(PlanAuditRequiredError, match="contribution"):
        build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    assert (tmp_path / "research/STATE.json").read_bytes() == before
    assert not (tmp_path / "review/bundles").exists()


def test_direct_approval_cannot_reuse_legacy_audit_to_bypass_contribution(tmp_path):
    active = _setup(tmp_path, verdict="pass")
    manifest = _mark(active)
    before = (tmp_path / "research/STATE.json").read_bytes()
    with pytest.raises(PlanAuditRequiredError, match="contribution"):
        require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=False)
    with pytest.raises(PlanAuditRequiredError, match="contribution"):
        approve_plan(tmp_path, EXPERIMENT_ID, "human_review")
    assert (tmp_path / "research/STATE.json").read_bytes() == before
    assert read_json(active / "MANIFEST.json") == manifest


@pytest.mark.parametrize("version", ["2.0", None, [], {}, 1])
def test_unknown_manifest_versions_fail_closed_before_mutation(tmp_path, version):
    active = _marked(tmp_path)
    manifest = _mark(active, version)
    state = (tmp_path / "research/STATE.json").read_bytes()
    for operation in (
        lambda: novelty_block_reason(tmp_path, EXPERIMENT_ID),
        lambda: plan_audit_input_hashes(tmp_path, active, manifest),
        lambda: prepare_decision(tmp_path, EXPERIMENT_ID, "novelty"),
    ):
        with pytest.raises(ValueError, match="unsupported novelty_contract_version"):
            operation()
    assert (tmp_path / "research/STATE.json").read_bytes() == state
    assert not (tmp_path / "review/decisions").exists()


@pytest.mark.parametrize("value", [None, [], 1, "invalid"])
def test_malformed_top_level_structures_fail_cleanly(value):
    assert novelty_evidence_errors(value, require_contribution=True)
    with pytest.raises(ValueError, match="manifest object"):
        novelty_contract_required(value)


@pytest.mark.parametrize("change", ["contribution", "marker"])
def test_bundle_contains_contribution_and_changes_invalidate_accepted_audit(tmp_path, change):
    active = _marked(tmp_path)
    manifest = _accept(tmp_path)
    request = read_json(tmp_path / f"review/bundles/{EXPERIMENT_ID}-plan/PLAN_AUDIT_REQUEST.json")
    assert request["novelty"] == _record()
    assert request["novelty_contract_version"] == "1.0"
    assert "novelty_contract_sha256" in request["audited_input_hashes"]
    require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=False)
    if change == "marker":
        del manifest["novelty_contract_version"]
        atomic_write_json(active / "MANIFEST.json", manifest)
    else:
        record = _record()
        record["contribution"]["advance"] = "Establish a narrower shift boundary."
        append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", record)
    with pytest.raises(PlanAuditRequiredError, match="inputs changed"):
        require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=False)


def test_complete_compact_novelty_response_is_accepted_by_decision_api(tmp_path):
    _marked(tmp_path)
    response = _compact_response()
    assert len(json.dumps(response).split()) <= 250
    folder = _respond(tmp_path, "novelty", "record_novelty")
    assert read_json(folder / "REQUEST.json")["novelty_contract_version"] == "1.0"
    atomic_write_json(folder / "RESPONSE.json", response)
    accept_decision(tmp_path, EXPERIMENT_ID, "novelty")
    assert (folder / "ACCEPTED.json").is_file()
    accepted = latest_novelty(tmp_path, EXPERIMENT_ID)
    assert accepted["contribution"] == response["novelty"]["contribution"]


@pytest.mark.parametrize("defect", [
    "missing", "source", "structure", "prediction", "risk", "record",
])
def test_rejected_agent_response_preserves_state_history_and_acceptance_markers(tmp_path, defect):
    active = _marked(tmp_path)
    folder = _respond(tmp_path, "novelty", "record_novelty")
    response = _compact_response()
    contribution = response["novelty"]["contribution"]
    if defect == "missing":
        del response["novelty"]["contribution"]
    elif defect == "source":
        contribution["source_observations"][0]["source"] = "invented-source"
    elif defect == "structure":
        response["novelty"]["contribution"] = []
    elif defect == "prediction":
        contribution["alternative_prediction"] = contribution["candidate_prediction"]
    elif defect == "risk":
        response["novelty"]["risk"] = []
    else:
        response["novelty"] = []
    atomic_write_json(folder / "RESPONSE.json", response)
    paths = [tmp_path / "research/STATE.json", active / "MANIFEST.json",
             tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"]
    before = {path: path.read_bytes() for path in paths}
    with pytest.raises(ValueError, match="source-backed evidence"):
        accept_decision(tmp_path, EXPERIMENT_ID, "novelty")
    assert all(path.read_bytes() == value for path, value in before.items())
    assert not (folder / "ACCEPTED.json").exists()
    assert not (folder / "APPLYING.json").exists()


@pytest.mark.parametrize("change", ["contribution", "marker"])
def test_changed_contribution_contract_invalidates_pending_decision(tmp_path, change):
    active = _marked(tmp_path)
    folder = _respond(tmp_path, "novelty", "record_novelty", novelty=_record())
    if change == "marker":
        manifest = read_json(active / "MANIFEST.json")
        del manifest["novelty_contract_version"]
        atomic_write_json(active / "MANIFEST.json", manifest)
    else:
        record = deepcopy(_record())
        record["contribution"]["advance"] = "Find a specific failure boundary."
        append_jsonl(tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl", record)
    before = (tmp_path / "research/STATE.json").read_bytes()
    with pytest.raises((ValueError, FileNotFoundError)):
        accept_decision(tmp_path, EXPERIMENT_ID, "novelty")
    assert (tmp_path / "research/STATE.json").read_bytes() == before
    assert not (folder / "ACCEPTED.json").exists()
