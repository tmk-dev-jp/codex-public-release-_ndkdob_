from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from test_plan_audit import EXPERIMENT_ID, REPO_ROOT, _accept
from test_plan_audit import _root as planned_root

import scripts.mark_implemented as implementation_module
import scripts.repair_context as repair_module
from scripts.build_implementation_review_bundle import implementation_audit_input_hashes
from scripts.common import atomic_write_json, read_json, run_script, sha256_file, sha256_path_set
from scripts.implementation_delta import (
    complete_implementation_delta,
    lock_implementation_delta,
)
from scripts.next_agent_action import PROFILE_AGENTS, next_agent_action
from scripts.next_autonomous_step import next_autonomous_step
from scripts.records import plan_hash
from scripts.repair_context import prepare_repair_context, repair_status


def _failed_root(root: Path, *, profile="balanced", comparison=False, audit=False):
    active = planned_root(root)
    record_path = active / "EXPERIMENT.md"
    record = record_path.read_text(encoding="utf-8").replace(
        "Implementation profile: balanced", f"Implementation profile: {profile}"
    )
    record_path.write_text(record, encoding="utf-8")
    manifest = read_json(active / "MANIFEST.json")
    config = read_json(REPO_ROOT / "configs/templates/smoke.json")
    config["experiment"].update(id=EXPERIMENT_ID, output_dir=f"artifacts/results/{EXPERIMENT_ID}")
    if comparison:
        config["comparison"] = {
            "arms": [
                {"id": "reference", "purpose": "matched control", "model": config["model"]},
                {"id": "candidate", "purpose": "test the core claim", "model": config["model"]},
            ],
            "conditions": [{"id": "main", "purpose": "matched condition", "data_parameters": {}}],
            "seeds": [17],
            "primary": {"candidate": "candidate", "reference": "reference"},
            "aggregation": "paired_mean",
            "max_total_batches": 14,
        }
    config_path = root / manifest["config"]
    atomic_write_json(config_path, config)
    manifest.update(
        stage="smoke",
        result_dir=f"artifacts/results/{EXPERIMENT_ID}",
        plan_sha256=plan_hash(record_path, config_path, active / "SCOPE.json"),
        locked_config_sha256=sha256_file(config_path),
    )
    _, manifest["implementation_delta"] = lock_implementation_delta(
        root, EXPERIMENT_ID, record, read_json(active / "SCOPE.json"), manifest["config"]
    )
    atomic_write_json(active / "MANIFEST.json", manifest)
    manifest = _accept(root)
    source = root / "src/change.py"
    source.write_text(
        "def transform(value):\n    # PRIVATE_SOURCE_DETAIL\n    return value + 2\n",
        encoding="utf-8",
    )
    _, manifest["implementation_delta"] = complete_implementation_delta(root, active, manifest)
    manifest.update(
        phase="FAILED",
        implementation_files=["src/change.py"],
        implementation_sha256=sha256_path_set(root, ["src/change.py"]),
        supervisor_conversation="PRIVATE_SUPERVISOR_TRANSCRIPT",
    )
    atomic_write_json(active / "MANIFEST.json", manifest)
    state = read_json(root / "research/STATE.json")
    state.update(
        phase="FAILED",
        review_policy={"independent_stages": ["smoke", "pilot", "full"]},
        next_action={
            "mode": "debug_failure",
            "queue_id": "Q-001",
            "objective": "PRIVATE_DEBUG_OBJECTIVE",
        },
    )
    atomic_write_json(root / "research/STATE.json", state)
    atomic_write_json(root / "experiments/INDEX.json", {"experiments": [{"id": EXPERIMENT_ID}]})
    if audit:
        path = active / "IMPLEMENTATION_AUDIT.md"
        path.write_text(
            "- Verdict: fail\n- Blocking issue: transform violates the declared behavior\n"
            "- Required action: correct the declared function\n",
            encoding="utf-8",
        )
        manifest["implementation_audit"] = {
            "verdict": "fail",
            "audit_sha256": sha256_file(path),
            "audited_inputs": implementation_audit_input_hashes(root, active, manifest),
        }
        atomic_write_json(active / "MANIFEST.json", manifest)
    else:
        atomic_write_json(
            root / manifest["result_dir"] / "error.json",
            {
                "experiment_id": EXPERIMENT_ID,
                "phase": "SANITY_PASSED",
                "error_type": "ValueError",
                "message": "PRIVATE_FAILURE_DETAIL",
            },
        )
    return active


@pytest.mark.parametrize("profile", PROFILE_AGENTS)
@pytest.mark.parametrize("audit", [False, True])
def test_repair_builds_before_delegation_and_keeps_details_out_of_supervisor(
    tmp_path, profile, audit
):
    _failed_root(tmp_path, profile=profile, audit=audit)
    action = next_agent_action(tmp_path, "repair", EXPERIMENT_ID)
    assert action.startswith("action=build builder=repair_context")
    route = next_autonomous_step(tmp_path)
    assert route.startswith("ready ") and "operation=repair" in route
    assert "PRIVATE_DEBUG_OBJECTIVE" not in route
    path = prepare_repair_context(tmp_path, EXPERIMENT_ID)
    request = read_json(path)
    assert len(path.read_text(encoding="utf-8")) <= 6000
    assert request["profile"] == profile
    assert request["failure"]["kind"] == ("implementation_audit" if audit else "execution_error")
    assert "PRIVATE_SOURCE_DETAIL" not in path.read_text(encoding="utf-8")
    assert "PRIVATE_SUPERVISOR_TRANSCRIPT" not in path.read_text(encoding="utf-8")
    action = next_agent_action(tmp_path, "repair", EXPERIMENT_ID)
    assert f"agent={PROFILE_AGENTS[profile]}" in action
    assert "task=repair context=isolated" in action
    assert "PRIVATE_FAILURE_DETAIL" not in action
    before = path.read_bytes()
    assert prepare_repair_context(tmp_path, EXPERIMENT_ID) == path
    assert path.read_bytes() == before


def test_real_repair_is_verified_compactly_and_returns_to_pre_run_audit(tmp_path, monkeypatch):
    active = _failed_root(tmp_path)
    request = prepare_repair_context(tmp_path, EXPERIMENT_ID)
    source = tmp_path / "src/change.py"
    source.write_text("def transform(value):\n    return value + 1\n", encoding="utf-8")
    namespace = {}
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    assert namespace["transform"](3) == 4
    monkeypatch.setattr(implementation_module, "tune_training_controls", lambda *args: None)
    implementation_module.mark_implemented(tmp_path, EXPERIMENT_ID)
    result = repair_status(tmp_path, EXPERIMENT_ID)
    assert "status=implemented repair=1 changed_files=1 next=review_implementation" in result
    assert "PRIVATE" not in result and len(result) < 200
    assert request.exists()  # Failure context survives result-dir cleanup.
    assert read_json(active / "MANIFEST.json")["implementation_audit"] is None
    source.write_text("def transform(value):\n    return value + 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after recording"):
        repair_status(tmp_path, EXPERIMENT_ID)


@pytest.mark.parametrize(
    "defect", ["plan", "failure", "missing-failure", "scope", "large", "transcript"]
)
def test_mechanical_blockers_do_not_dispatch_a_worker(tmp_path, monkeypatch, defect):
    active = _failed_root(tmp_path)
    manifest = read_json(active / "MANIFEST.json")
    error_path = tmp_path / manifest["result_dir"] / "error.json"
    if defect == "plan":
        record = (active / "EXPERIMENT.md").read_text(encoding="utf-8")
        (active / "EXPERIMENT.md").write_text(record.replace("0.01", "0.001"), encoding="utf-8")
    elif defect == "failure":
        error = read_json(error_path)
        error["experiment_id"] = "EXP-OTHER"
        atomic_write_json(error_path, error)
    elif defect == "missing-failure":
        error_path.unlink()
    elif defect == "scope":
        scope = read_json(active / "SCOPE.json")
        scope["write_paths"].append("src/another.py")
        atomic_write_json(active / "SCOPE.json", scope)
    elif defect == "large":
        monkeypatch.setattr(repair_module, "MAX_REQUEST_CHARS", 1000)
    else:
        error = read_json(error_path)
        error["transcript"] = "DO_NOT_FORWARD"
        atomic_write_json(error_path, error)
    with pytest.raises((OSError, ValueError)):
        next_agent_action(tmp_path, "repair", EXPERIMENT_ID)
    assert not (tmp_path / "review/repairs").exists()


def test_changed_or_stale_context_cannot_be_used_for_completion(tmp_path, monkeypatch):
    _failed_root(tmp_path, audit=True)
    path = prepare_repair_context(tmp_path, EXPERIMENT_ID)
    request = read_json(path)
    request["failure"]["required_action"] = "different action"
    atomic_write_json(path, request)
    with pytest.raises(ValueError, match="do not overwrite"):
        prepare_repair_context(tmp_path, EXPERIMENT_ID)
    (tmp_path / "src/change.py").write_text(
        "def transform(value):\n    return value + 1\n", encoding="utf-8"
    )
    monkeypatch.setattr(implementation_module, "tune_training_controls", lambda *args: None)
    implementation_module.mark_implemented(tmp_path, EXPERIMENT_ID)
    with pytest.raises(ValueError, match="context hash changed"):
        repair_status(tmp_path, EXPERIMENT_ID)


def test_repair_cannot_change_undeclared_symbols(tmp_path, monkeypatch):
    _failed_root(tmp_path)
    prepare_repair_context(tmp_path, EXPERIMENT_ID)
    (tmp_path / "src/change.py").write_text(
        "def transform(value):\n    return value + 1\n\ndef unrelated():\n    return 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(implementation_module, "tune_training_controls", lambda *args: None)
    with pytest.raises(ValueError, match="undeclared symbol"):
        implementation_module.mark_implemented(tmp_path, EXPERIMENT_ID)
    assert read_json(tmp_path / "research/STATE.json")["phase"] == "FAILED"


def test_later_failure_gets_a_new_request_without_previous_debug_context(tmp_path, monkeypatch):
    active = _failed_root(tmp_path)
    first = prepare_repair_context(tmp_path, EXPERIMENT_ID)
    original = first.read_bytes()
    source = tmp_path / "src/change.py"
    source.write_text("def transform(value):\n    return value + 1\n", encoding="utf-8")
    monkeypatch.setattr(implementation_module, "tune_training_controls", lambda *args: None)
    implementation_module.mark_implemented(tmp_path, EXPERIMENT_ID)
    manifest = read_json(active / "MANIFEST.json")
    manifest["phase"] = "FAILED"
    atomic_write_json(active / "MANIFEST.json", manifest)
    state = read_json(tmp_path / "research/STATE.json")
    state.update(phase="FAILED", next_action={"mode": "debug_failure"})
    atomic_write_json(tmp_path / "research/STATE.json", state)
    atomic_write_json(
        tmp_path / manifest["result_dir"] / "error.json",
        {"experiment_id": EXPERIMENT_ID, "error_type": "ValueError", "message": "NEW_FAILURE"},
    )
    assert next_agent_action(tmp_path, "repair", EXPERIMENT_ID).startswith("action=build ")
    second = prepare_repair_context(tmp_path, EXPERIMENT_ID)
    assert second != first and first.read_bytes() == original
    assert read_json(second)["sequence"] == 2
    assert "NEW_FAILURE" in second.read_text(encoding="utf-8")
    assert "PRIVATE_FAILURE_DETAIL" not in second.read_text(encoding="utf-8")
    source.write_text("def transform(value):\n    return value\n", encoding="utf-8")
    implementation_module.mark_implemented(tmp_path, EXPERIMENT_ID)
    assert "status=implemented repair=2" in repair_status(tmp_path, EXPERIMENT_ID)


def test_repair_context_does_not_import_ml_and_status_is_one_line(tmp_path, monkeypatch, capsys):
    _failed_root(tmp_path)
    monkeypatch.setattr(repair_module, "root_from_script", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["repair_context.py", "status", "--id", EXPERIMENT_ID])
    assert run_script("repair-context", repair_module._execute) == 0
    output = capsys.readouterr()
    assert output.out.count("\n") == 1 and output.err == ""
    assert "PRIVATE_FAILURE_DETAIL" not in output.out
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import scripts.repair_context; assert 'torch' not in sys.modules",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_worker_and_supervisor_contracts_prevent_debug_transcript_returns():
    skill = (REPO_ROOT / ".agents/skills/debug-failure/SKILL.md").read_text(encoding="utf-8")
    assert "Do not open REQUEST.json in the supervisor" in skill
    assert "without inherited conversation" in skill
    for name in ("mechanical-implementer", "experiment-implementer", "scientific-implementer"):
        text = (REPO_ROOT / ".codex/agents" / f"{name}.toml").read_text(encoding="utf-8")
        assert "task=repair" in text and "80 words" in text
