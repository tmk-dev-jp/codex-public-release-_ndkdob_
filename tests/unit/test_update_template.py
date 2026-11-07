from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import update_template as updater


def git(root: Path, *args: str) -> str:
    return (
        subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
        .decode()
        .strip()
    )


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit(root: Path) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repos(tmp_path):
    source, target = tmp_path / "template", tmp_path / "project"
    source.mkdir()
    target.mkdir()
    for repo in (source, target):
        git(repo, "init", "-q")
        git(repo, "config", "core.filemode", "true")
        write(repo, "scripts/a.py", "old\n")
        write(repo, "scripts/deleted.py", "remove\n")
        write(repo, "research/CONTEXT.md", "private\n")
        write(repo, ".codex/config.toml", "local\n")
        commit(repo)
    old = git(source, "rev-parse", "HEAD")
    write(source, "scripts/a.py", "new\n")
    write(source, "scripts/new.py", "added\n")
    (source / "scripts/deleted.py").unlink()
    write(source, "research/CONTEXT.md", "template research\n")
    write(source, ".codex/config.toml", "template config\n")
    new = commit(source)
    args = argparse.Namespace(
        root=str(target),
        template=str(source),
        from_ref=old,
        to_ref=new,
        path=None,
        plan=None,
        apply=False,
    )
    return source, target, args


def test_preview_apply_preserves_state_and_reads_git_blobs(repos, tmp_path):
    source, target, args = repos
    head, index = git(target, "rev-parse", "HEAD"), (target / ".git/index").read_bytes()
    write(source, "scripts/a.py", "dirty source\n")
    write(source, "scripts/untracked.py", "untracked source\n")
    args.plan = str(tmp_path / "plan.json")
    assert "preview files=3" in updater.update(args)
    assert (target / "scripts/a.py").read_text() == "old\n"
    assert len(json.loads(Path(args.plan).read_text())["changes"]) == 3
    args.plan = None
    args.apply = True
    message = updater.update(args)
    assert "applied files=3" in message
    backup = Path(message.split("backup=", 1)[1])
    assert (backup / "files/scripts/a.py").read_text() == "old\n"
    assert (target / "scripts/a.py").read_text() == "new\n"
    assert (target / "scripts/new.py").read_text() == "added\n"
    assert not (target / "scripts/deleted.py").exists()
    assert (target / "research/CONTEXT.md").read_text() == "private\n"
    assert (target / ".codex/config.toml").read_text() == "local\n"
    assert git(target, "rev-parse", "HEAD") == head
    assert (target / ".git/index").read_bytes() == index
    assert "applied files=0" in updater.update(args)


@pytest.mark.parametrize(
    "collision", ["modified", "staged", "untracked", "ignored", "symlink", "ancestor"]
)
def test_conflicts_leave_entire_batch_untouched(repos, collision, tmp_path):
    _, target, args = repos
    if collision == "modified":
        write(target, "scripts/deleted.py", "local edit\n")
    elif collision == "staged":
        write(target, "scripts/deleted.py", "staged edit\n")
        git(target, "add", "scripts/deleted.py")
    elif collision in {"untracked", "ignored"}:
        write(target, "scripts/new.py", "collision\n")
        if collision == "ignored":
            write(target, ".git/info/exclude", "scripts/new.py\n")
    elif collision == "symlink":
        (target / "scripts/new.py").symlink_to(tmp_path / "outside")
    else:
        (target / "scripts/a.py").unlink()
        (target / "scripts/deleted.py").unlink()
        (target / "scripts").rmdir()
        write(target, "scripts", "file\n")
    index = (target / ".git/index").read_bytes()
    args.apply = True
    with pytest.raises(ValueError):
        updater.update(args)
    if collision != "ancestor":
        assert (target / "scripts/a.py").read_text() == "old\n"
    assert (target / ".git/index").read_bytes() == index


def test_repeat_update_of_tracked_file_and_executable_mode(repos):
    source, target, args = repos
    (source / "scripts/a.py").chmod(0o755)
    args.to_ref = commit(source)
    args.path = ["scripts/a.py"]
    args.apply = True
    assert "files=1" in updater.update(args)
    assert (target / "scripts/a.py").stat().st_mode & stat.S_IXUSR
    assert "files=0" in updater.update(args)


@pytest.mark.parametrize(
    "name",
    [
        "research/CONTEXT.md",
        ".codex/config.toml",
        "scripts/../../outside",
        "/tmp/outside",
        "data/file",
    ],
)
def test_protected_or_escaping_selection_rejected(repos, name):
    _, _, args = repos
    args.path = [name]
    with pytest.raises(ValueError, match="allowlist"):
        updater.update(args)


def test_source_symlink_rejected(repos):
    source, _, args = repos
    (source / "scripts/new.py").unlink()
    (source / "scripts/new.py").symlink_to("../../outside")
    args.to_ref = commit(source)
    with pytest.raises(ValueError, match="unsupported"):
        updater.update(args)


def test_failure_rolls_back_and_leaves_backup(repos, monkeypatch):
    _, target, args = repos
    original = updater.replace_file
    failed = False

    def fail_once(path, payload, mode):
        nonlocal failed
        if path.name == "new.py" and not failed:
            failed = True
            raise OSError("injected write failure")
        return original(path, payload, mode)

    monkeypatch.setattr(updater, "replace_file", fail_once)
    args.apply = True
    with pytest.raises(OSError, match="injected"):
        updater.update(args)
    assert (target / "scripts/a.py").read_text() == "old\n"
    assert (target / "scripts/deleted.py").read_text() == "remove\n"
    assert not (target / "scripts/new.py").exists()


def test_cli_error_is_one_bounded_line(repos):
    _, _, args = repos
    result = subprocess.run(
        [
            sys.executable,
            str(Path(updater.__file__)),
            "--template",
            args.template,
            "--from-ref",
            "missing",
            "--to-ref",
            args.to_ref,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert not result.stdout
    assert result.stderr.startswith("ERROR update_template:")
    assert result.stderr.count("\n") == 1


@pytest.mark.parametrize(
    "name",
    [
        "scripts/.env",
        "scripts/.env.local",
        "scripts/venv/file.py",
        "scripts/__pycache__/file.pyc",
    ],
)
def test_nested_protected_files_are_excluded(repos, name):
    source, target, args = repos
    write(source, name, "protected payload")
    args.to_ref = commit(source)
    args.apply = True
    updater.update(args)
    assert not (target / name).exists()


def test_git_environment_overrides_rejected(repos, monkeypatch):
    _, target, args = repos
    monkeypatch.setenv("GIT_INDEX_FILE", str(target / "alternate-index"))
    with pytest.raises(ValueError, match="GIT_"):
        updater.update(args)
    assert not (target / "alternate-index").exists()


def test_literal_pathspec_does_not_match_other_staged_files(repos):
    source, target, args = repos
    name = "scripts/[a].py"
    write(source, name, "old bracket\n")
    args.from_ref = commit(source)
    write(target, name, "old bracket\n")
    commit(target)
    write(source, name, "new bracket\n")
    args.to_ref = commit(source)
    write(target, "scripts/a.py", "staged unrelated\n")
    git(target, "add", "scripts/a.py")
    args.path = [name]
    args.apply = True
    updater.update(args)
    assert (target / name).read_text() == "new bracket\n"
    assert git(target, "diff", "--cached", "--name-only") == "scripts/a.py"


def test_nested_git_directory_is_never_managed():
    assert not updater.managed("human/.git/config")


@pytest.fixture
def github_transport(repos, monkeypatch):
    source, _, args = repos
    git(source, "tag", "template-v1", args.from_ref)
    git(
        source, "-c", "user.name=Test", "-c", "user.email=test@example.test",
        "tag", "-am", "annotated release", "template-v2", args.to_ref,
    )
    args.github = "example/template"
    args.template = None
    args.from_ref = "template-v1"
    args.to_ref = "template-v2"
    original = updater.git
    fetched = []

    def transport(repo, *command, public=False):
        if command[0] == "fetch":
            assert public
            assert "--depth=1" in command
            assert "--no-tags" in command
            assert "--no-recurse-submodules" in command
            assert command[5] == "https://github.com/example/template.git"
            fetched.append(repo)
            command = (*command[:5], str(source), *command[6:])
        return original(repo, *command, public=public)

    monkeypatch.setattr(updater, "git", transport)
    return args, fetched


def test_github_tags_preview_apply_and_cleanup(repos, github_transport, tmp_path):
    _, target, _ = repos
    args, fetched = github_transport
    args.plan = str(tmp_path / "github-plan.json")
    assert "preview files=3" in updater.update(args)
    plan = json.loads(Path(args.plan).read_text())
    assert plan["repository"] == "https://github.com/example/template"
    assert plan["from_tag"] == "template-v1"
    assert plan["to_tag"] == "template-v2"
    assert (target / "scripts/a.py").read_text() == "old\n"
    args.plan = None
    args.apply = True
    assert "applied files=3" in updater.update(args)
    assert (target / "scripts/a.py").read_text() == "new\n"
    assert "files=0" in updater.update(args)
    assert all(not directory.exists() for directory in fetched)


@pytest.mark.parametrize("repository", ["../template", "example/template/extra",
                                         "https://github.com/example/template", "example/.."])
def test_invalid_github_repository_rejected(repos, repository):
    _, target, args = repos
    args.github = repository
    args.apply = True
    with pytest.raises(ValueError, match="--github"):
        updater.update(args)
    assert (target / "scripts/a.py").read_text() == "old\n"


@pytest.mark.parametrize("tag", ["missing", "HEAD", "template-v2^{commit}", "--all"])
def test_github_requires_existing_exact_tag(repos, github_transport, tag):
    _, target, _ = repos
    args, _ = github_transport
    args.to_ref = tag
    args.apply = True
    with pytest.raises(ValueError):
        updater.update(args)
    assert (target / "scripts/a.py").read_text() == "old\n"


def test_github_conflict_still_stops_entire_batch(repos, github_transport):
    _, target, _ = repos
    args, _ = github_transport
    write(target, "scripts/deleted.py", "local\n")
    args.apply = True
    with pytest.raises(ValueError, match="conflicts"):
        updater.update(args)
    assert (target / "scripts/a.py").read_text() == "old\n"
    assert (target / "scripts/deleted.py").read_text() == "local\n"


def test_public_transport_disables_config_and_prompts(tmp_path, monkeypatch):
    calls = []

    def capture(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(updater.subprocess, "run", capture)
    updater.git(tmp_path, "fetch", "https://github.com/example/template.git", public=True)
    _, options = calls[0]
    assert options["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert options["env"]["GIT_CONFIG_GLOBAL"] == updater.os.devnull
    assert options["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert options["env"]["GIT_ASKPASS"] == ""
    assert options["env"]["SSH_ASKPASS"] == ""
    assert options["timeout"] == 120
