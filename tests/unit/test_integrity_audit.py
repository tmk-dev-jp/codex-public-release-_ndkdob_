from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.accept_implementation_audit import accept_implementation_audit
from scripts.accept_integrity_audit import accept_integrity_audit
from scripts.build_implementation_review_bundle import (
    ImplementationAuditRequiredError,
    build_implementation_review_bundle,
    require_accepted_implementation_audit,
)
from scripts.build_plan_review_bundle import plan_audit_input_hashes
from scripts.build_review_bundle import audit_input_hashes
from scripts.common import sha256_file, sha256_path_set
from scripts.implementation_delta import (
    complete_implementation_delta,
    lock_implementation_delta,
)
from scripts.records import plan_hash


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _research_context_inputs(root: Path) -> None:
    (root / "research").mkdir(parents=True, exist_ok=True)
    (root / "research/GOAL.md").write_text("# Research Goal\n", encoding="utf-8")
    (root / "experiments").mkdir(parents=True, exist_ok=True)
    (root / "experiments/DIGEST.md").write_text("# Digest\n", encoding="utf-8")


def _delta_record(experiment_id: str) -> str:
    return f"""# {experiment_id}

## Hypothesis

- Claim: a scoped mechanism may improve the metric

## Method

- Implementation: change one declared target
- Baseline behavior: the baseline returns the current representation
- Candidate behavior: the candidate applies one representation change
- Intervention point: src/model.py module state
- Unchanged invariants: data split metric seed and training budget

## Conclusion

- Decision: pending

## Issues and Next Direction

- Main issue: pending
"""


def test_accept_integrity_warn_routes_to_evaluation(tmp_path: Path) -> None:
    experiment_id = "EXP-TEST"
    _research_context_inputs(tmp_path)
    _write_json(
        tmp_path / "research/STATE.json",
        {
            "project_id": "test",
            "project_status": "active",
            "active_experiment": experiment_id,
            "phase": "REVIEW_REQUIRED",
            "stage": "pilot",
            "review_required": True,
            "budgets": {"max_context_chars": 9000},
            "next_action": {"mode": "review_required", "queue_id": "Q-001"},
        },
    )
    active = tmp_path / f"experiments/active/{experiment_id}"
    manifest = {
            "id": experiment_id,
            "phase": "REVIEW_REQUIRED",
            "queue_id": "Q-001",
            "config": f"configs/experiments/{experiment_id}.json",
            "result_dir": f"artifacts/results/{experiment_id}",
            "plan_sha256": "plan-hash",
            "implementation_sha256": "implementation-hash",
        }
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(tmp_path / f"configs/experiments/{experiment_id}.json", {})
    (active / "EXPERIMENT.md").write_text(
        _delta_record(experiment_id), encoding="utf-8"
    )
    scope = {
        "read_paths": [],
        "write_paths": [],
        "test_paths": [],
        "change_targets": [],
        "planning_reads": [],
        "implementation_entry_reads": [],
    }
    _write_json(active / "SCOPE.json", scope)
    _, delta_metadata = lock_implementation_delta(
        tmp_path,
        experiment_id,
        _delta_record(experiment_id),
        scope,
        manifest["config"],
    )
    manifest["implementation_delta"] = delta_metadata
    _, delta_metadata = complete_implementation_delta(
        tmp_path, active, manifest
    )
    manifest["implementation_delta"] = delta_metadata
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(tmp_path / f"artifacts/results/{experiment_id}/metrics.json", {})
    _write_json(tmp_path / f"artifacts/results/{experiment_id}/manifest.json", {})
    _write_json(
        tmp_path / f"experiments/active/{experiment_id}/DECISION_FACTS.json",
        {"experiment_id": experiment_id},
    )
    _write_json(
        tmp_path / "experiments/INDEX.json",
        {"experiments": [{"id": experiment_id, "phase": "REVIEW_REQUIRED"}]},
    )
    bundle = tmp_path / f"review/bundles/{experiment_id}"
    bundle.mkdir(parents=True)
    (bundle / "REQUEST.json").write_text("{}\n", encoding="utf-8")
    (bundle / "INTEGRITY_AUDIT.md").write_text(
        f"""# Integrity Audit for {experiment_id}

## Verdict

- Verdict: warn
- Result provenance: metrics and manifest agree
- Plan adherence: implementation matches the locked scope
- Metric validity: primary metric is computed as configured
- Data leakage and split risk: split evidence is limited to manifest metadata
- Scope discipline: claim must remain limited to this pilot

## Required Action

- Blocking issue: none
- Required action: carry the split caveat into evaluation
""",
        encoding="utf-8",
    )

    accepted = accept_integrity_audit(tmp_path, experiment_id)

    manifest = json.loads(
        (tmp_path / f"experiments/active/{experiment_id}/MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    state = json.loads((tmp_path / "research/STATE.json").read_text(encoding="utf-8"))
    assert accepted.name == "INTEGRITY_AUDIT.md"
    assert manifest["integrity_audit"]["verdict"] == "warn"
    assert "audit_sha256" in manifest["integrity_audit"]
    assert "metrics_sha256" in manifest["integrity_audit"]["audited_inputs"]
    assert state["next_action"]["mode"] == "review_required"

    _write_json(tmp_path / f"artifacts/results/{experiment_id}/metrics.json", {"changed": True})
    active = tmp_path / f"experiments/active/{experiment_id}"
    assert manifest["integrity_audit"]["audited_inputs"] != audit_input_hashes(
        tmp_path, active, manifest
    )


def test_accept_implementation_warn_and_invalidate_changed_plan_or_code(
    tmp_path: Path,
) -> None:
    experiment_id = "EXP-IMPLEMENTATION"
    _research_context_inputs(tmp_path)
    active = tmp_path / f"experiments/active/{experiment_id}"
    record_path = active / "EXPERIMENT.md"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        f"""# {experiment_id}

## Hypothesis

- Claim: a scoped mechanism may improve the metric

## Method

- Implementation: change one model file
- Baseline behavior: the model module stores VALUE zero
- Candidate behavior: the model module stores VALUE one
- Intervention point: src/model.py module state
- Unchanged invariants: data split metric seed and training budget

## Conclusion

- Decision: pending
- Mechanical rule status: pending

## Issues and Next Direction

- Main issue: pending
""",
        encoding="utf-8",
    )
    config_path = tmp_path / f"configs/experiments/{experiment_id}.json"
    scope_path = active / "SCOPE.json"
    implementation_path = tmp_path / "src/model.py"
    _write_json(config_path, {})
    _write_json(
        scope_path,
        {
            "read_paths": [],
            "write_paths": ["src/model.py"],
            "test_paths": [],
            "change_targets": [
                {
                    "path": "src/model.py",
                    "role": "intervention",
                    "action": "modify",
                    "symbols": ["<module>"],
                }
            ],
            "planning_reads": [],
            "implementation_entry_reads": [],
        },
    )
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_path.write_text("VALUE = 0\n", encoding="utf-8")
    _write_json(
        tmp_path / "research/STATE.json",
        {
            "project_id": "test",
            "project_status": "active",
            "active_experiment": experiment_id,
            "phase": "IMPLEMENTED",
            "stage": "pilot",
            "review_required": True,
            "budgets": {"max_context_chars": 9000},
            "review_policy": {"independent_stages": ["pilot", "full"]},
            "next_action": {
                "mode": "review_implementation",
                "queue_id": "Q-001",
            },
        },
    )
    manifest = {
        "id": experiment_id,
        "phase": "IMPLEMENTED",
        "queue_id": "Q-001",
        "stage": "pilot",
        "baseline_id": None,
        "config": f"configs/experiments/{experiment_id}.json",
        "result_dir": f"artifacts/results/{experiment_id}",
        "plan_sha256": plan_hash(record_path, config_path, scope_path),
        "locked_config_sha256": sha256_file(config_path),
        "implementation_files": ["src/model.py"],
        "implementation_sha256": sha256_path_set(tmp_path, ["src/model.py"]),
        "implementation_audit": None,
        "plan_audit": None,
    }
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    _, delta_metadata = lock_implementation_delta(
        tmp_path,
        experiment_id,
        record_path.read_text(encoding="utf-8"),
        scope,
        manifest["config"],
    )
    manifest["implementation_delta"] = delta_metadata
    implementation_path.write_text("VALUE = 1\n", encoding="utf-8")
    manifest["implementation_sha256"] = sha256_path_set(
        tmp_path, ["src/model.py"]
    )
    _, delta_metadata = complete_implementation_delta(
        tmp_path, active, manifest
    )
    manifest["implementation_delta"] = delta_metadata
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(
        tmp_path / "research/TRAINING_CONTROLS.json",
        {"schema_version": "1.0", "policy": {"reuse": "locked by stage"}},
    )
    (active / "PLAN_AUDIT.md").write_text(
        "# Accepted Plan Audit\n", encoding="utf-8"
    )
    manifest["plan_audit"] = {
        "verdict": "pass",
        "audit_sha256": sha256_file(active / "PLAN_AUDIT.md"),
        "audited_inputs": plan_audit_input_hashes(tmp_path, active, manifest),
    }
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(
        tmp_path / "experiments/INDEX.json",
        {"experiments": [{"id": experiment_id, "phase": "IMPLEMENTED"}]},
    )
    template = tmp_path / "experiments/templates/IMPLEMENTATION_AUDIT.md"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("# Implementation Audit for {{EXPERIMENT_ID}}\n", encoding="utf-8")

    bundle = build_implementation_review_bundle(tmp_path, experiment_id)
    (bundle / "IMPLEMENTATION_AUDIT.md").write_text(
        f"""# Implementation Audit for {experiment_id}

## Verdict

- Verdict: warn
- Plan fidelity: implementation follows the locked method
- Data split and leakage: no split handling changed
- Loss and optimization: no optimization defect found
- Metric implementation: metric path matches the plan
- Reproducibility and checkpointing: deterministic controls remain active
- Scope and minimality: only the scoped model file changed
- Declared implementation delta: observed module change matches the declaration

## Required Action

- Blocking issue: none
- Required action: retain the scope caveat
""",
        encoding="utf-8",
    )

    accepted = accept_implementation_audit(tmp_path, experiment_id)
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    state = json.loads((tmp_path / "research/STATE.json").read_text(encoding="utf-8"))
    assert accepted.name == "IMPLEMENTATION_AUDIT.md"
    assert manifest["implementation_audit"]["verdict"] == "warn"
    assert state["next_action"]["mode"] == "implemented"

    evaluated_record = record_path.read_text(encoding="utf-8").replace(
        "- Decision: pending", "- Decision: supported"
    )
    record_path.write_text(evaluated_record, encoding="utf-8")
    require_accepted_implementation_audit(tmp_path, state, active, manifest)

    record_path.write_text(
        evaluated_record.replace(
            "a scoped mechanism may improve the metric",
            "a different mechanism may improve the metric",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ImplementationAuditRequiredError):
        require_accepted_implementation_audit(tmp_path, state, active, manifest)

    record_path.write_text(evaluated_record, encoding="utf-8")
    implementation_path.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ImplementationAuditRequiredError):
        require_accepted_implementation_audit(tmp_path, state, active, manifest)
