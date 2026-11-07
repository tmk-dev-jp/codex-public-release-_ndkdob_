from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.abort_comparison as abort_module
from scripts.abort_comparison import abort_comparison
from scripts.build_decision_facts import load_baseline_payload
from scripts.build_digest import build_digest
from scripts.common import atomic_write_json, read_json
from scripts.new_experiment import create_experiment

ROOT = Path(__file__).resolve().parents[2]
ID = "EXP-ABORT"
REASON = "Data contract failure requires a revised plan"


def _failed_root(root):
    active = root / f"experiments/active/{ID}"
    result = root / f"artifacts/results/{ID}"
    manifest = {
        "id": ID,
        "phase": "FAILED",
        "status": "active",
        "stage": "smoke",
        "queue_id": "Q-001",
        "config": f"configs/experiments/{ID}.json",
        "result_dir": f"artifacts/results/{ID}",
        "record": f"experiments/active/{ID}/EXPERIMENT.md",
    }
    atomic_write_json(active / "MANIFEST.json", manifest)
    atomic_write_json(root / manifest["config"], {"comparison": {"arms": ["fixture"]}})
    atomic_write_json(active / "SCOPE.json", {})
    (active / "EXPERIMENT.md").write_text(
        "# Experiment\n\n## Hypothesis\n\nlocked claim\n\n## Method\n\nlocked method\n"
        "\n## Conclusion\n\n- Decision: pending\n\n## Issues and Next Direction\n\n",
        encoding="utf-8",
    )
    atomic_write_json(result / "comparison_state.json", {"status": "failed"})
    atomic_write_json(result / "runs/R001/metrics.json", {"status": "completed", "value": 0.9})
    (result / "runs/R001/best.pt").write_bytes(b"untouched checkpoint fixture")
    atomic_write_json(result / "error.json", {"error_type": "ValueError"})
    atomic_write_json(root / f"review/bundles/{ID}/REQUEST.json", {"preserve": True})
    atomic_write_json(
        root / "research/STATE.json",
        {
            "project_status": "active",
            "active_experiment": ID,
            "phase": "FAILED",
            "stage": "smoke",
            "latest_completed_experiment": "EXP-PREVIOUS",
            "baseline_experiment": None,
            "review_required": False,
            "approvals": {"plan_review_experiment_id": ID, "full_training_experiment_id": ID},
            "budgets": {"max_context_chars": 9000, "max_completed_digest_rows": 20},
            "unattended_loop": {"status": "in_progress", "target_experiment": ID},
            "next_action": {"mode": "debug_failure", "queue_id": "Q-001"},
        },
    )
    atomic_write_json(root / "experiments/INDEX.json", {"experiments": [manifest.copy()]})
    (root / "research/GOAL.md").write_text("# Research Goal\n", encoding="utf-8")
    for name in ("EVIDENCE.jsonl", "CLAIMS.jsonl"):
        (root / "research" / name).write_text("", encoding="utf-8")
    return active, result


def _abort(root, **kwargs):
    return abort_comparison(root, ID, reason=REASON, confirm_abort=True, **kwargs)


def test_abort_preserves_evidence_and_frees_only_the_active_slot(tmp_path):
    active, result = _failed_root(tmp_path)
    record = (active / "EXPERIMENT.md").read_bytes()
    manifest = read_json(active / "MANIFEST.json")
    preserved = [
        tmp_path / manifest["config"],
        result / "comparison_state.json",
        result / "runs/R001/metrics.json",
        result / "runs/R001/best.pt",
        result / "error.json",
        tmp_path / f"review/bundles/{ID}/REQUEST.json",
        tmp_path / "research/EVIDENCE.jsonl",
        tmp_path / "research/CLAIMS.jsonl",
    ]
    before = [path.read_bytes() for path in preserved]
    archived = _abort(tmp_path)
    assert archived == tmp_path / f"experiments/aborted/{ID}"
    assert not active.exists()
    assert (archived / "EXPERIMENT.md").read_bytes() == record
    closure = read_json(archived / "ABORTION.json")
    assert closure["original_manifest"] == manifest
    assert closure["scientific_outcome"] == "not_evaluated"
    assert read_json(archived / "MANIFEST.json")["phase"] == "ABORTED"
    assert [path.read_bytes() for path in preserved] == before
    state = read_json(tmp_path / "research/STATE.json")
    assert state["active_experiment"] is None and state["phase"] is None
    assert state["latest_completed_experiment"] == "EXP-PREVIOUS"
    assert state["latest_aborted_experiment"] == ID
    assert state["baseline_experiment"] is None
    assert set(state["approvals"].values()) == {None}
    assert state["unattended_loop"]["status"] == "idle"
    assert state["next_action"]["mode"] == "select_experiment"
    digest = (tmp_path / "experiments/DIGEST.md").read_text(encoding="utf-8")
    assert REASON in digest and "not accepted evidence" in digest
    assert ID in (tmp_path / "research/CONTEXT.md").read_text(encoding="utf-8")
    before_state = (tmp_path / "research/STATE.json").read_bytes()
    assert _abort(tmp_path) == archived
    assert (tmp_path / "research/STATE.json").read_bytes() == before_state


@pytest.mark.parametrize("reason, confirm", [(REASON, False), ("", True), ("x" * 401, True)])
def test_abort_requires_explicit_confirmation_and_reason(tmp_path, reason, confirm):
    active, _ = _failed_root(tmp_path)
    state = (tmp_path / "research/STATE.json").read_bytes()
    with pytest.raises(ValueError):
        abort_comparison(tmp_path, ID, reason=reason, confirm_abort=confirm)
    assert active.is_dir() and not (active / "ABORTION.json").exists()
    assert (tmp_path / "research/STATE.json").read_bytes() == state


@pytest.mark.parametrize("defect", ["phase", "no-progress", "missing-index", "occupied-archive"])
def test_abort_refuses_invalid_target_before_writes(tmp_path, defect):
    active, result = _failed_root(tmp_path)
    if defect == "phase":
        state = read_json(tmp_path / "research/STATE.json")
        state["phase"] = "SANITY_PASSED"
        atomic_write_json(tmp_path / "research/STATE.json", state)
    elif defect == "no-progress":
        (result / "comparison_state.json").unlink()
    elif defect == "missing-index":
        atomic_write_json(tmp_path / "experiments/INDEX.json", {"experiments": []})
    else:
        (tmp_path / f"experiments/aborted/{ID}").mkdir(parents=True)
    with pytest.raises((ValueError, FileExistsError)):
        _abort(tmp_path)
    assert active.is_dir() and not (active / "ABORTION.json").exists()


@pytest.mark.parametrize("cut", ["closure", "move", "manifest", "index", "state", "digest"])
def test_explicit_repeat_finishes_interrupted_closure_without_retraining(
    tmp_path, monkeypatch, cut
):
    active, result = _failed_root(tmp_path)
    checkpoint = (result / "runs/R001/best.pt").read_bytes()
    write = abort_module.atomic_write_json
    rename = Path.rename
    digest = abort_module.build_digest

    def fail_write(path, payload):
        target = {
            "closure": "ABORTION.json",
            "manifest": "MANIFEST.json",
            "index": "INDEX.json",
            "state": "STATE.json",
        }.get(cut)
        if path.name == target:
            raise OSError("interrupted closure")
        write(path, payload)

    def fail_move(path, target):
        if path == active:
            raise OSError("interrupted closure")
        return rename(path, target)

    def fail_digest(root):
        raise OSError("interrupted closure")

    monkeypatch.setattr(abort_module, "atomic_write_json", fail_write)
    if cut == "move":
        monkeypatch.setattr(Path, "rename", fail_move)
    if cut == "digest":
        monkeypatch.setattr(abort_module, "build_digest", fail_digest)
    with pytest.raises(OSError, match="interrupted closure"):
        _abort(tmp_path)
    monkeypatch.setattr(abort_module, "atomic_write_json", write)
    monkeypatch.setattr(Path, "rename", rename)
    monkeypatch.setattr(abort_module, "build_digest", digest)
    assert _abort(tmp_path).is_dir()
    assert (result / "runs/R001/best.pt").read_bytes() == checkpoint
    assert read_json(tmp_path / "research/STATE.json")["active_experiment"] is None


def test_changed_inputs_or_reason_cannot_overwrite_closure(tmp_path):
    _, result = _failed_root(tmp_path)
    archived = _abort(tmp_path)
    before = (archived / "ABORTION.json").read_bytes()
    with pytest.raises(ValueError, match="reason differs"):
        abort_comparison(tmp_path, ID, reason="new reason", confirm_abort=True)
    atomic_write_json(result / "comparison_state.json", {"changed": True})
    with pytest.raises(ValueError, match="inputs changed"):
        _abort(tmp_path)
    assert (archived / "ABORTION.json").read_bytes() == before


def test_abort_is_not_a_baseline_and_cannot_reuse_id(tmp_path):
    _failed_root(tmp_path)
    _abort(tmp_path)
    with pytest.raises(ValueError, match="cannot supply baseline"):
        load_baseline_payload(tmp_path, ID)
    (tmp_path / f"configs/experiments/{ID}.json").unlink()
    with pytest.raises(ValueError, match="already indexed"):
        create_experiment(tmp_path, experiment_id=ID, stage="smoke")
    assert not (tmp_path / f"experiments/active/{ID}").exists()


def test_new_id_requires_a_new_draft_and_old_abort_cannot_change_it(tmp_path):
    _failed_root(tmp_path)
    _abort(tmp_path)
    for relative in (
        "configs/templates/smoke.json",
        "experiments/templates/EXPERIMENT.md",
        "experiments/templates/SCOPE.json",
        "experiments/templates/MANIFEST.json",
        "experiments/templates/EXPERIMENT_AGENTS.md",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    draft = create_experiment(tmp_path, experiment_id="EXP-NEW", stage="smoke")
    assert read_json(draft / "MANIFEST.json")["phase"] == "DRAFT"
    state_before = (tmp_path / "research/STATE.json").read_bytes()
    with pytest.raises(ValueError, match="not the active"):
        _abort(tmp_path)
    assert (tmp_path / "research/STATE.json").read_bytes() == state_before


def test_abort_cli_is_one_line_and_imports_no_torch():
    result = subprocess.run(
        [sys.executable, "scripts/abort_comparison.py", "--id", ID, "--reason", REASON],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and result.stdout == ""
    assert result.stderr.startswith("ERROR abort-comparison:")
    assert result.stderr.count("\n") == 1
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import scripts.abort_comparison; assert 'torch' not in sys.modules",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_aborted_digest_is_bounded_without_hiding_the_full_reason(tmp_path):
    _failed_root(tmp_path)
    reason = "A" * 400
    entries = [
        {"id": f"EXP-{number}", "status": "aborted", "stage": "smoke", "abort_reason": reason}
        for number in range(8)
    ]
    atomic_write_json(tmp_path / "experiments/INDEX.json", {"experiments": entries})
    text = build_digest(tmp_path).read_text(encoding="utf-8")
    assert "EXP-2" not in text and "EXP-3" in text and "EXP-7" in text
    assert "A" * 158 not in text
    assert len(text) < 1500
    assert read_json(tmp_path / "experiments/INDEX.json")["experiments"] == entries
