from __future__ import annotations

import json
import sys

import pytest
from test_agent_gate import EXPERIMENT_ID as GATE_ID
from test_agent_gate import (
    _accept_plan_audit,
    _base_root,
    _completed_implementation_audit,
    _completed_integrity_audit,
    _copy_template,
)
from test_autonomous_loop import _cleared_novelty
from test_plan_audit import EXPERIMENT_ID, _audit
from test_plan_audit import _root as audit_root

import scripts.compress_audit_material as compression
from scripts.accept_implementation_audit import accept_implementation_audit
from scripts.accept_integrity_audit import accept_integrity_audit
from scripts.accept_plan_audit import accept_plan_audit
from scripts.build_implementation_review_bundle import build_implementation_review_bundle
from scripts.build_plan_review_bundle import build_plan_review_bundle, plan_audit_input_hashes
from scripts.build_review_bundle import build_review_bundle
from scripts.common import atomic_write_json, read_json, run_script, sha256_file, sha256_path_set
from scripts.next_agent_action import TASK_FIELDS, next_agent_action
from scripts.next_autonomous_step import next_autonomous_step
from scripts.next_unattended_loop_step import next_unattended_loop_step
from scripts.records import compact_record_format, field, normalize_record_format

BOILERPLATE = "Review the previously documented scientific finding carefully. "


def _bundle(root):
    active = audit_root(root)
    _cleared_novelty(root, EXPERIMENT_ID)
    return active, build_plan_review_bundle(root, EXPERIMENT_ID)


def _long_report(bundle):
    repeated = BOILERPLATE * 80
    text = (
        _audit("warn")
        .replace(
            "- Required action: preserve the diagnostic-only guardrail",
            "- Required action: " + repeated + "preserve the diagnostic-only guardrail",
        )
        .replace(
            "- Blocking issue: none",
            "- Blocking issue: no adoption unless `src/change.py` reaches >= 0.05; "
            "preliminary evidence",
        )
    )
    (bundle / "PLAN_AUDIT.md").write_text(text, encoding="utf-8")
    return repeated


def test_builder_packs_oversized_input_without_altering_a_scientific_value(tmp_path):
    active, bundle = _bundle(tmp_path)
    request = read_json(bundle / "PLAN_AUDIT_REQUEST.json")
    template = (bundle / "PLAN_AUDIT.md").read_text(encoding="utf-8")
    pretty_size = len(json.dumps(request, indent=2) + "\n") + len(template)
    goal = request["goal"] + "x" * (9000 - pretty_size + 100)
    (tmp_path / "research/GOAL.md").write_text(goal, encoding="utf-8")
    protected = {
        path: path.read_bytes()
        for path in (
            active / "EXPERIMENT.md",
            active / "SCOPE.json",
            active / "MANIFEST.json",
            tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json",
            tmp_path / "research/STATE.json",
        )
    }
    build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    packed = (bundle / "PLAN_AUDIT_REQUEST.json").read_text(encoding="utf-8")
    restored = json.loads(packed)
    assert len(packed) + len(template) <= 9000
    assert len(json.dumps(restored, indent=2)) + len(template) > 9000
    assert restored["goal"] == goal
    assert restored["locked_plan"] == request["locked_plan"]
    assert restored["audited_input_hashes"] == plan_audit_input_hashes(
        tmp_path, active, read_json(active / "MANIFEST.json")
    )
    assert all(path.read_bytes() == content for path, content in protected.items())
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).startswith("action=delegate ")


def test_existing_large_request_routes_through_compression_in_the_same_loop_phase(tmp_path):
    _, bundle = _bundle(tmp_path)
    request_path = bundle / "PLAN_AUDIT_REQUEST.json"
    request = read_json(request_path)
    template = (bundle / "PLAN_AUDIT.md").read_text(encoding="utf-8")
    budget = len(compression.compact_json_text(request)) + len(template) + 10
    state = read_json(tmp_path / "research/STATE.json")
    state["budgets"]["max_plan_audit_chars"] = budget
    atomic_write_json(tmp_path / "research/STATE.json", state)
    before = (tmp_path / "research/STATE.json").read_bytes()
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).endswith("target=request")
    assert next_autonomous_step(tmp_path).startswith("ready mode=audit_experiment_plan ")
    route = next_unattended_loop_step(tmp_path, explicit_user_request=True)
    assert "action=run-phase skill=$audit-experiment-plan" in route
    # Persisted loop progress is not a phase transition or a new approval.
    state_after_route = read_json(tmp_path / "research/STATE.json")
    assert state_after_route["phase"] == json.loads(before)["phase"]
    assert "status=ready" in compression.compress_audit_material(
        tmp_path, EXPERIMENT_ID, "plan-audit"
    )
    assert read_json(request_path) == request
    assert len(request_path.read_text(encoding="utf-8")) + len(template) <= budget
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).startswith("action=delegate ")


def test_identical_report_fields_shrink_without_a_new_judgment_and_fail_stays_fail(tmp_path):
    active, bundle = _bundle(tmp_path)
    report = bundle / "PLAN_AUDIT.md"
    original = _audit("fail") * 3
    report.write_text(original, encoding="utf-8")
    assert len(normalize_record_format(original).split()) > 250
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).endswith("target=report")
    assert "status=ready" in compression.compress_audit_material(
        tmp_path, EXPERIMENT_ID, "plan-audit"
    )
    compact = report.read_text(encoding="utf-8")
    assert len(normalize_record_format(compact).split()) <= 250
    assert all(
        field(compact, label) == field(original, label) for label in TASK_FIELDS["plan-audit"]
    )
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).startswith("action=accept ")
    accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert read_json(active / "MANIFEST.json")["plan_audit"]["verdict"] == "fail"
    assert "reason=plan-audit-pass-required" in next_unattended_loop_step(
        tmp_path, explicit_user_request=True
    )


def test_unaccepted_report_can_be_shortened_and_accepted_without_reauditing(tmp_path):
    active, bundle = _bundle(tmp_path)
    repeated = _long_report(bundle)
    result = compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    assert "status=needs-edit" in result
    archive = tmp_path / "review/compression" / EXPERIMENT_ID / "plan-audit"
    original = (archive / "ORIGINAL.md").read_bytes()
    candidate = archive / "CANDIDATE.md"
    candidate.write_text(
        candidate.read_text(encoding="utf-8").replace(repeated, BOILERPLATE), encoding="utf-8"
    )
    assert "status=ready" in compression.compress_audit_material(
        tmp_path, EXPERIMENT_ID, "plan-audit", apply=True
    )
    assert (archive / "ORIGINAL.md").read_bytes() == original
    assert not (bundle / "CANDIDATE.md").exists()
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID).startswith("action=accept ")
    accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert read_json(active / "MANIFEST.json")["plan_audit"]["verdict"] == "warn"


@pytest.mark.parametrize(
    "change",
    ["verdict", "number", "path", "qualification", "field", "extra", "finding", "comparison"],
)
def test_shortening_rejects_changed_protected_findings(tmp_path, change):
    _, bundle = _bundle(tmp_path)
    repeated = _long_report(bundle)
    compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    archive = tmp_path / "review/compression" / EXPERIMENT_ID / "plan-audit"
    candidate = archive / "CANDIDATE.md"
    text = candidate.read_text(encoding="utf-8").replace(repeated, BOILERPLATE)
    changes = {
        "verdict": ("Verdict: warn", "Verdict: pass"),
        "number": ("0.05", "0.01"),
        "path": ("src/change.py", "src/other.py"),
        "qualification": ("unless", "after"),
        "field": ("- Blocking issue:", "- Missing assessment:"),
        "extra": ("# Plan Audit", "# Changed title"),
        "finding": ("nuisance selection could raise accuracy alone", "none"),
        "comparison": (">=", "<="),
    }
    candidate.write_text(text.replace(*changes[change]), encoding="utf-8")
    before = (bundle / "PLAN_AUDIT.md").read_bytes()
    with pytest.raises(ValueError):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit", apply=True)
    assert (bundle / "PLAN_AUDIT.md").read_bytes() == before


def test_irreducible_input_cannot_raise_limits_or_erase_existing_material(tmp_path):
    _, bundle = _bundle(tmp_path)
    state_path = tmp_path / "research/STATE.json"
    state = read_json(state_path)
    state["budgets"]["max_plan_audit_chars"] = 1
    atomic_write_json(state_path, state)
    before = {path: path.read_bytes() for path in (state_path, *bundle.iterdir())}
    assert (
        "status=blocked reason=essential-inputs-exceed-budget"
        in compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    )
    with pytest.raises(ValueError, match="after lossless compression"):
        build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    assert all(path.read_bytes() == content for path, content in before.items())


def test_stale_inputs_and_accepted_evidence_are_not_rewritten(tmp_path):
    _, bundle = _bundle(tmp_path)
    request = bundle / "PLAN_AUDIT_REQUEST.json"
    before = request.read_bytes()
    (tmp_path / "research/GOAL.md").write_text("Changed scientific purpose", encoding="utf-8")
    with pytest.raises(ValueError, match="current, otherwise valid"):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    assert request.read_bytes() == before
    build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    (bundle / "PLAN_AUDIT.md").write_text(_audit(), encoding="utf-8")
    accept_plan_audit(tmp_path, EXPERIMENT_ID)
    with pytest.raises(ValueError):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")


def test_duplicate_json_keys_block_before_any_material_write(tmp_path):
    _, bundle = _bundle(tmp_path)
    (bundle / "EXTRA.json").write_text('{"risk":true,"risk":false}', encoding="utf-8")
    before = (bundle / "PLAN_AUDIT_REQUEST.json").read_bytes()
    with pytest.raises(ValueError, match="duplicate JSON"):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    assert (bundle / "PLAN_AUDIT_REQUEST.json").read_bytes() == before


def test_format_compaction_preserves_code_examples_and_conflicting_values():
    text = _audit() + "\n```text\n- Verdict: fail\n\n````\n"
    result = compact_record_format(text, TASK_FIELDS["plan-audit"])
    assert "- Verdict: fail\n\n````" in result
    with pytest.raises(ValueError, match="duplicate field"):
        compact_record_format(_audit() + "\n- Verdict: fail\n", TASK_FIELDS["plan-audit"])


def test_compression_cli_returns_only_one_compact_status_line(tmp_path, monkeypatch, capsys):
    _bundle(tmp_path)
    monkeypatch.setattr(compression, "root_from_script", lambda: tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["compress_audit_material.py", "--id", EXPERIMENT_ID, "--task", "plan-audit"]
    )
    assert run_script("compress-audit-material", compression._execute) == 0
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1 and not output.err
    assert "status=ready" in output.out and "nuisance" not in output.out


@pytest.mark.parametrize("task", ["implementation-audit", "integrity-audit"])
def test_other_audit_character_overflow_compacts_without_relaunching_auditor(tmp_path, task):
    implementation = task == "implementation-audit"
    active = _base_root(
        tmp_path,
        mode="review_implementation" if implementation else "review_required",
        phase="IMPLEMENTED" if implementation else "REVIEW_REQUIRED",
    )
    if implementation:
        state_path = tmp_path / "research/STATE.json"
        state = read_json(state_path)
        state["review_policy"] = {"independent_stages": ["pilot"]}
        atomic_write_json(state_path, state)
        manifest = read_json(active / "MANIFEST.json")
        manifest.update(
            stage="pilot",
            implementation_files=[],
            implementation_sha256=sha256_path_set(tmp_path, []),
        )
        atomic_write_json(active / "MANIFEST.json", manifest)
    _accept_plan_audit(tmp_path, active)
    if implementation:
        _copy_template(tmp_path, "IMPLEMENTATION_AUDIT.md")
        bundle = build_implementation_review_bundle(tmp_path, GATE_ID)
        report_name, content = "IMPLEMENTATION_AUDIT.md", _completed_implementation_audit()
    else:
        config_hash = sha256_file(tmp_path / f"configs/experiments/{GATE_ID}.json")
        result_dir = tmp_path / "artifacts/results" / GATE_ID
        atomic_write_json(
            result_dir / "metrics.json",
            {
                "experiment_id": GATE_ID,
                "baseline_id": None,
                "status": "completed",
                "config_sha256": config_hash,
                "primary_metric": {
                    "name": "test_accuracy",
                    "value": 0.72,
                    "direction": "maximize",
                    "decision_mode": "threshold",
                    "minimum_effect": 0.01,
                },
            },
        )
        atomic_write_json(
            result_dir / "manifest.json",
            {
                "experiment_id": GATE_ID,
                "config_sha256": config_hash,
            },
        )
        _copy_template(tmp_path, "INTEGRITY_AUDIT.md")
        _copy_template(tmp_path, "EVALUATION.md")
        bundle = build_review_bundle(tmp_path, GATE_ID)
        report_name, content = "INTEGRITY_AUDIT.md", _completed_integrity_audit()
    (bundle / report_name).write_text(content + "\n" * 10000, encoding="utf-8")
    source_hashes = {path: path.read_bytes() for path in active.iterdir() if path.is_file()}
    assert "target=report" in next_agent_action(tmp_path, task, GATE_ID)
    acceptor = accept_implementation_audit if implementation else accept_integrity_audit
    with pytest.raises(ValueError, match="compress-audit-material"):
        acceptor(tmp_path, GATE_ID)
    assert "status=ready" in compression.compress_audit_material(tmp_path, GATE_ID, task)
    assert len((bundle / report_name).read_text(encoding="utf-8")) <= 9000
    assert next_agent_action(tmp_path, task, GATE_ID).startswith("action=accept ")
    assert all(path.read_bytes() == value for path, value in source_hashes.items())
    acceptor(tmp_path, GATE_ID)
    manifest_key = "implementation_audit" if implementation else "integrity_audit"
    assert read_json(active / "MANIFEST.json")[manifest_key]["verdict"] == "pass"


def test_direct_acceptance_cannot_bypass_the_input_character_budget(tmp_path):
    active, bundle = _bundle(tmp_path)
    (bundle / "PLAN_AUDIT.md").write_text(_audit(), encoding="utf-8")
    request = bundle / "PLAN_AUDIT_REQUEST.json"
    request.write_text(json.dumps(read_json(request), indent=30), encoding="utf-8")
    assert len(request.read_text(encoding="utf-8")) > 9000
    with pytest.raises(ValueError, match="compress-audit-material"):
        accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert read_json(active / "MANIFEST.json")["plan_audit"] is None


def test_tampered_compression_archive_and_unchanged_long_candidate_cannot_apply(tmp_path):
    _, bundle = _bundle(tmp_path)
    _long_report(bundle)
    compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit")
    with pytest.raises(ValueError, match="still exceeds"):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit", apply=True)
    original = tmp_path / "review/compression" / EXPERIMENT_ID / "plan-audit/ORIGINAL.md"
    original.write_text(
        original.read_text(encoding="utf-8") + "Changed provenance\n", encoding="utf-8"
    )
    before = (bundle / "PLAN_AUDIT.md").read_bytes()
    with pytest.raises(ValueError, match="compression source changed"):
        compression.compress_audit_material(tmp_path, EXPERIMENT_ID, "plan-audit", apply=True)
    assert (bundle / "PLAN_AUDIT.md").read_bytes() == before
