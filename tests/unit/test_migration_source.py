from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import migration_source as migration


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "old research"
    folder.mkdir()
    (folder / ".gitignore").write_text(
        "private.py\n*.json\n!config.json\nbuild/\n*.log\n", encoding="utf-8"
    )
    (folder / "README.md").write_text("Old project\n", encoding="utf-8")
    (folder / "private.py").write_text("DO_NOT_READ", encoding="utf-8")
    (folder / "config.json").write_text('{"task": "regression"}', encoding="utf-8")
    (folder / "secret.json").write_text("DO_NOT_READ", encoding="utf-8")
    return folder


def _paths(payload):
    return {entry["path"] for entry in payload["entries"]}


def test_non_git_source_lists_only_eligible_paths_without_modification(source):
    before = sorted(source.iterdir())
    result = migration.inspect_source(source)
    assert _paths(result) == {".gitignore", "README.md", "config.json"}
    assert sorted(source.iterdir()) == before and not (source / ".git").exists()
    assert len(result["gitignore_sha256"]) == 64


def test_source_ignore_policy_applies_even_to_force_tracked_files(source):
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "-f", "private.py"], check=True)
    with pytest.raises(ValueError, match="gitignore denies"):
        migration.inspect_source(source, "private.py", read=True)
    assert "private.py" not in _paths(migration.inspect_source(source))


def test_nested_rules_and_root_relative_patterns_use_git_semantics(source):
    package = source / "package"
    package.mkdir()
    (package / ".gitignore").write_text("*.py\n!keep.py\n/root-only.txt\n", encoding="utf-8")
    for name in ("hidden.py", "keep.py", "root-only.txt"):
        (package / name).write_text("fixture", encoding="utf-8")
    nested = package / "nested"
    nested.mkdir()
    (nested / "root-only.txt").write_text("allowed", encoding="utf-8")
    assert _paths(migration.inspect_source(source, "package")) == {
        "package/.gitignore",
        "package/keep.py",
        "package/nested",
    }
    assert migration.inspect_source(source, "package/nested/root-only.txt", read=True)["text"]
    with pytest.raises(ValueError, match="gitignore denies"):
        migration.inspect_source(source, "package/hidden.py", read=True)


def test_ignored_parent_cannot_be_reopened_by_nested_negation(source):
    build = source / "build"
    build.mkdir()
    (build / ".gitignore").write_text("!keep.py\n", encoding="utf-8")
    (build / "keep.py").write_text("DO_NOT_READ", encoding="utf-8")
    with pytest.raises(ValueError, match="gitignore denies"):
        migration.inspect_source(source, "build/keep.py", read=True)
    assert "build" not in _paths(migration.inspect_source(source))


def test_source_and_global_git_configuration_do_not_control_policy(source, tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    (source / ".git/info/exclude").write_text("README.md\n", encoding="utf-8")
    global_ignore = tmp_path / "global-ignore"
    global_ignore.write_text("README.md\nconfig.json\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.excludesFile")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(global_ignore))
    assert "README.md" in _paths(migration.inspect_source(source))
    assert migration.inspect_source(source, "config.json", read=True)["text"]


def test_policy_is_rechecked_before_every_read(source):
    assert migration.inspect_source(source, "README.md", read=True)["text"]
    (source / ".gitignore").write_text("README.md\n", encoding="utf-8")
    with pytest.raises(ValueError, match="gitignore denies"):
        migration.inspect_source(source, "README.md", read=True)


def test_missing_policy_does_not_default_to_full_access(source):
    (source / ".gitignore").unlink()
    with pytest.raises(ValueError, match="regular .gitignore"):
        migration.inspect_source(source)


def test_root_policy_is_bootstrap_readable_when_ignored(source):
    (source / ".gitignore").write_text("*\n", encoding="utf-8")
    assert migration.inspect_source(source, ".gitignore", read=True)["text"] == "*\n"
    assert not _paths(migration.inspect_source(source))


@pytest.mark.parametrize("relative", ["private.py", "secret.json", ".env", "data/raw.txt"])
def test_denied_file_content_is_never_opened(source, relative, monkeypatch):
    candidate = source / relative
    candidate.parent.mkdir(exist_ok=True)
    candidate.write_text("DO_NOT_READ", encoding="utf-8")
    original = Path.read_bytes

    def guard(path):
        assert path != candidate, "denied content was opened"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guard)
    with pytest.raises(ValueError):
        migration.inspect_source(source, relative, read=True)


def test_discovery_does_not_descend_into_payloads_or_nested_repositories(source, monkeypatch):
    for name in ("data", "artifacts", "references", "results", "vendor", ".venv"):
        (source / name).mkdir()
    (source / "vendor/.git").write_text("gitdir: elsewhere", encoding="utf-8")
    original = Path.iterdir

    def shallow(path):
        assert path == source, "discovery recursed into a child directory"
        return original(path)

    monkeypatch.setattr(Path, "iterdir", shallow)
    assert _paths(migration.inspect_source(source)) == {".gitignore", "README.md", "config.json"}


@pytest.mark.parametrize("relative", ["../outside.md", "/tmp/outside.md", r"folder\file.py"])
def test_path_escape_is_rejected(source, relative):
    with pytest.raises(ValueError, match="source-relative"):
        migration.inspect_source(source, relative, read=True)


def test_symlinks_and_redirected_nested_policies_are_rejected(source, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("DO_NOT_READ", encoding="utf-8")
    (source / "alias.md").symlink_to(outside)
    with pytest.raises(ValueError, match="symlinks"):
        migration.inspect_source(source, "alias.md", read=True)
    assert "alias.md" not in _paths(migration.inspect_source(source))
    nested = source / "code"
    nested.mkdir()
    (nested / ".gitignore").symlink_to(outside)
    with pytest.raises(ValueError, match="redirected"):
        migration.inspect_source(source, "code")


def test_policy_size_is_checked_even_for_root_discovery(source):
    (source / ".gitignore").write_text("#" * 65537, encoding="utf-8")
    with pytest.raises(ValueError, match="policy read budget"):
        migration.inspect_source(source)


def test_template_source_overlap_is_rejected():
    with pytest.raises(ValueError, match="must not overlap"):
        migration.inspect_source(migration._REPO_ROOT)


def test_source_code_data_package_is_not_treated_as_raw_data(source):
    package = source / "src/project/data"
    package.mkdir(parents=True)
    (package / "loader.py").write_text("def load():\n    return 1\n", encoding="utf-8")
    assert (
        "def load"
        in migration.inspect_source(source, "src/project/data/loader.py", read=True)["text"]
    )


def test_extensionless_license_can_be_reviewed_as_text(source):
    (source / "LICENSE").write_text("User-managed project license\n", encoding="utf-8")
    assert migration.inspect_source(source, "LICENSE", read=True)["text"].startswith("User-managed")


def test_git_failure_blocks_read_without_forwarding_git_output(source, monkeypatch, capsys):
    def fail(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, b"PRIVATE_GIT_OUTPUT", b"private error")

    monkeypatch.setattr(migration.subprocess, "run", fail)
    assert (
        migration.main(
            [
                "read",
                "--source",
                str(source),
                "--path",
                "README.md",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert not output.out and "PRIVATE_GIT_OUTPUT" not in output.err
    assert len(output.err.splitlines()) == 1


def test_read_ranges_hashes_and_json_preserve_code_whitespace(source, capsys):
    path = source / "model.py"
    content = "def model():\n    return 'two  spaces'\n"
    path.write_text(content, encoding="utf-8")
    assert (
        migration.main(
            [
                "read",
                "--source",
                str(source),
                "--path",
                "model.py",
                "--lines",
                "1",
            ]
        )
        == 0
    )
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1 and not output.err
    payload = json.loads(output.out.removeprefix("OK migration-source "))
    assert payload["text"] == "def model():\n" and payload["next_line"] == 2
    next_page = migration.inspect_source(source, "model.py", read=True, start_line=2)
    assert next_page["text"] == "    return 'two  spaces'\n"
    assert next_page["sha256"] == payload["sha256"] and next_page["next_line"] is None


def test_pagination_is_explicit_and_bounded(source):
    first = migration.inspect_source(source, limit=2)
    second = migration.inspect_source(source, offset=first["next_offset"], limit=2)
    assert len(first["entries"]) == 2 and second["next_offset"] is None
    assert _paths(first).isdisjoint(_paths(second))
    assert _paths(first) | _paths(second) == _paths(migration.inspect_source(source))


@pytest.mark.parametrize("defect", ["binary", "large", "output", "notebook", "range"])
def test_read_budgets_and_non_text_rejection(source, defect):
    name, content, kwargs = "model.py", b"x = 1\n", {}
    if defect == "binary":
        content = b"\0binary"
    elif defect == "large":
        content = b"#" * (migration.MAX_FILE_BYTES + 1)
    elif defect == "output":
        content = b"#" * (migration.MAX_OUTPUT_CHARS + 1)
    elif defect == "notebook":
        name = "model.ipynb"
    else:
        kwargs = {"start_line": 0}
    (source / name).write_bytes(content)
    with pytest.raises(ValueError):
        migration.inspect_source(source, name, read=True, **kwargs)


def test_cli_error_is_one_line_without_source_content(source, capsys):
    assert (
        migration.main(
            [
                "read",
                "--source",
                str(source),
                "--path",
                "private.py",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert not output.out and len(output.err.splitlines()) == 1
    assert output.err.startswith("ERROR migration-source:") and "DO_NOT_READ" not in output.err


def test_direct_script_entry_reads_without_mutating_source(source):
    result = subprocess.run(
        [
            sys.executable,
            str(Path(migration.__file__)),
            "read",
            "--source",
            str(source),
            "--path",
            "README.md",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and not result.stderr
    assert len(result.stdout.splitlines()) == 1
    payload = json.loads(result.stdout.removeprefix("OK migration-source "))
    assert payload["text"] == "Old project\n" and not (source / ".git").exists()
