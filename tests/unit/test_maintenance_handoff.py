from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.maintenance_handoff as handoff
from scripts.common import atomic_write_json, read_json, run_script

ROOT = Path(__file__).resolve().parents[2]


def _git(root, *args):
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "maintenance").mkdir()
    shutil.copy2(
        ROOT / "maintenance/TASK.template.json", tmp_path / "maintenance/TASK.template.json"
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "src/module.py", "maintenance/TASK.template.json")
    _git(tmp_path, "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
    task = read_json(tmp_path / "maintenance/TASK.template.json")
    task.update(
        objective="Improve one module",
        scope=["src/module.py"],
        read_next=["src/module.py"],
        summary=["Implemented the scoped behavior."],
        next_steps=["Run the focused regression test."],
        constraints=["Preserve existing uncommitted changes."],
        checks=[{"command": "touch DO_NOT_EXECUTE", "result": "not_run", "detail": "Not run."}],
    )
    atomic_write_json(tmp_path / handoff.TASK, task)
    return tmp_path


def test_save_and_check_are_scoped_read_only_and_do_not_execute_notes(workspace):
    atomic_write_json(workspace / "research/STATE.json", {"active_experiment": "EXP-OTHER"})
    atomic_write_json(workspace / "data/private.json", {"private": True})
    before = (workspace / "research/STATE.json").read_bytes()
    entry = handoff.save_handoff(workspace)
    assert handoff.check_handoff(workspace).startswith("status=current")
    snapshot = read_json(workspace / handoff.SNAPSHOT)
    assert set(snapshot["files"]) == {"src/module.py"}
    assert "VALUE = 1" not in entry.read_text(encoding="utf-8")
    assert len(entry.read_text(encoding="utf-8")) <= 6000
    assert not (workspace / "DO_NOT_EXECUTE").exists()
    assert (workspace / "research/STATE.json").read_bytes() == before
    files = [workspace / name for name in (handoff.TASK, handoff.SNAPSHOT, handoff.ENTRY)]
    saved = [path.read_bytes() for path in files]
    handoff.check_handoff(workspace)
    assert [path.read_bytes() for path in files] == saved


@pytest.mark.parametrize("mutation", ["edit", "delete", "new", "read-next", "task", "entry", "git"])
def test_changes_are_reported_without_rewriting_saved_notes(workspace, mutation):
    task = read_json(workspace / handoff.TASK)
    task["scope"].append("src/future.py")
    task["read_next"].append("README.md")
    atomic_write_json(workspace / handoff.TASK, task)
    source = workspace / "src/module.py"
    source.write_text("VALUE = 2\n", encoding="utf-8")
    handoff.save_handoff(workspace)
    snapshot = (workspace / handoff.SNAPSHOT).read_bytes()
    if mutation == "edit":
        source.write_text("VALUE = 3\n", encoding="utf-8")
    elif mutation == "delete":
        source.unlink()
    elif mutation == "new":
        (workspace / "src/future.py").write_text("VALUE = 4\n", encoding="utf-8")
    elif mutation == "read-next":
        (workspace / "README.md").write_text("Changed context\n", encoding="utf-8")
    elif mutation == "task":
        task["objective"] = "Changed objective"
        atomic_write_json(workspace / handoff.TASK, task)
    elif mutation == "entry":
        (workspace / handoff.ENTRY).write_text("Changed entry\n", encoding="utf-8")
    else:
        _git(workspace, "checkout", "-qb", "another-branch")
    result = handoff.check_handoff(workspace)
    assert result.startswith("status=stale action=review-changes")
    if mutation == "edit":
        assert "files=src/module.py" in result
        assert "git-state" not in result
    assert (workspace / handoff.SNAPSHOT).read_bytes() == snapshot


def test_complete_is_not_a_new_assignment_and_commits_require_review(workspace):
    task = read_json(workspace / handoff.TASK)
    task.update(status="complete", next_steps=[])
    atomic_write_json(workspace / handoff.TASK, task)
    handoff.save_handoff(workspace)
    assert "action=report-complete" in handoff.check_handoff(workspace)
    _git(workspace, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "new head")
    assert "git-state" in handoff.check_handoff(workspace)


def test_blocked_handoff_retains_the_blocker_without_authorizing_work(workspace):
    task = read_json(workspace / handoff.TASK)
    task.update(
        status="blocked", next_steps=["Ask the user to decide the unresolved API contract."]
    )
    atomic_write_json(workspace / handoff.TASK, task)
    handoff.save_handoff(workspace)
    assert "action=review-blocker" in handoff.check_handoff(workspace)


@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "/tmp/outside",
        ".git/config",
        "data/private.json",
        "artifacts/result.json",
        "references/paper.pdf",
        "experiments/active/EXP-X/EXPERIMENT.md",
        "experiments/completed/EXP-X/EXPERIMENT.md",
        "experiments/aborted/EXP-X/EXPERIMENT.md",
        "review/bundles/EXP-X/REQUEST.json",
        "src",
        "src/*.py",
        handoff.TASK,
        handoff.ENTRY,
    ],
)
def test_unsafe_or_broad_scope_is_rejected_before_saving(workspace, path):
    task = read_json(workspace / handoff.TASK)
    task["scope"] = [path]
    atomic_write_json(workspace / handoff.TASK, task)
    with pytest.raises(ValueError):
        handoff.save_handoff(workspace)
    assert not (workspace / handoff.SNAPSHOT).exists()


def test_symlinks_cannot_expand_scope_or_redirect_outputs(workspace):
    (workspace / "src/link.py").symlink_to(workspace / "src/module.py")
    task = read_json(workspace / handoff.TASK)
    task["scope"] = ["src/link.py"]
    atomic_write_json(workspace / handoff.TASK, task)
    with pytest.raises(ValueError, match="symlink"):
        handoff.save_handoff(workspace)
    task["scope"] = ["src/module.py"]
    atomic_write_json(workspace / handoff.TASK, task)
    (workspace / handoff.ENTRY).symlink_to(workspace / "src/module.py")
    with pytest.raises(ValueError, match="symlink"):
        handoff.save_handoff(workspace)
    assert (workspace / "src/module.py").read_text(encoding="utf-8") == "VALUE = 1\n"


@pytest.mark.parametrize("budget", ["file", "total", "entry", "record", "paths"])
def test_capture_budgets_fail_without_replacing_previous_snapshot(workspace, monkeypatch, budget):
    handoff.save_handoff(workspace)
    before = (workspace / handoff.SNAPSHOT).read_bytes()
    task = read_json(workspace / handoff.TASK)
    if budget == "file":
        monkeypatch.setattr(handoff, "MAX_FILE_BYTES", 5)
    elif budget == "total":
        monkeypatch.setattr(handoff, "MAX_TOTAL_BYTES", 5)
    elif budget == "entry":
        for label in ("summary", "decisions", "constraints"):
            task[label] = ["x" * 400] * 6
    elif budget == "paths":
        task["scope"] = [f"src/file{i}.py" for i in range(41)]
    atomic_write_json(workspace / handoff.TASK, task)
    if budget == "record":
        (workspace / handoff.TASK).write_bytes(b" " * (handoff.MAX_RECORD_BYTES + 1))
    with pytest.raises(ValueError):
        handoff.save_handoff(workspace)
    assert (workspace / handoff.SNAPSHOT).read_bytes() == before


def test_protected_payload_changes_do_not_pollute_maintenance_snapshot(workspace):
    handoff.save_handoff(workspace)
    atomic_write_json(workspace / "artifacts/results/EXP-X/metrics.json", {"value": 1})
    assert handoff.check_handoff(workspace).startswith("status=current")


def test_init_preserves_existing_work_and_missing_is_explicit(workspace):
    assert handoff.check_handoff(workspace) == "status=missing action=create-handoff"
    before = (workspace / handoff.TASK).read_bytes()
    with pytest.raises(FileExistsError):
        handoff.initialize_handoff(workspace, "New objective")
    assert (workspace / handoff.TASK).read_bytes() == before
    (workspace / handoff.TASK).unlink()
    path = handoff.initialize_handoff(workspace, "New objective")
    assert read_json(path)["objective"] == "New objective"
    with pytest.raises(ValueError, match="next step"):
        handoff.save_handoff(workspace)


def test_cli_output_is_one_line(workspace, monkeypatch, capsys):
    monkeypatch.setattr(handoff, "root_from_script", lambda: workspace)
    for action in ("save", "check"):
        monkeypatch.setattr(sys, "argv", ["maintenance_handoff.py", action])
        assert run_script("maintenance-handoff", handoff._execute) == 0
        output = capsys.readouterr()
        assert output.err == "" and output.out.count("\n") == 1
        assert output.out.startswith("OK maintenance-handoff")
    monkeypatch.setattr(sys, "argv", ["maintenance_handoff.py", "bad-action"])
    assert run_script("maintenance-handoff", handoff._execute) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err.count("\n") == 1
    assert output.err.startswith("ERROR maintenance-handoff")


def test_handoff_import_does_not_load_ml_libraries():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import scripts.maintenance_handoff; assert 'torch' not in sys.modules",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
