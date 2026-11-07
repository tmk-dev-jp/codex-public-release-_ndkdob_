import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.reproducibility_checkpoint import CheckpointError, checkpoint

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/reproducibility_checkpoint.py"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "commit.gpgsign", "false")
    for name in ("code.py", "config.json", "requirements.txt", "manifest.json", "other.txt"):
        (tmp_path / name).write_text("initial\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def run(root, tag="experiment-v1", paths=None):
    return checkpoint(
        root,
        tag,
        paths or ["code.py"],
        ["config.json"],
        ["requirements.txt"],
        ["manifest.json"],
        "Experiment inputs",
    )


def test_scoped_commit_preserves_unrelated_staged_and_dirty_files(repo):
    (repo / "code.py").write_text("changed\n")
    (repo / "other.txt").write_text("staged\n")
    git(repo, "add", "other.txt")
    (repo / "other.txt").write_text("also dirty\n")
    (repo / "new.py").write_text("new code\n")
    before = git(repo, "diff", "--cached", "--binary", "--", "other.txt")
    head = git(repo, "rev-parse", "HEAD").strip()
    assert run(repo, paths=["code.py", "new.py"]).startswith("commit=")
    assert git(repo, "rev-parse", "HEAD^").strip() == head
    assert git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines() == [
        b"code.py",
        b"new.py",
    ]
    assert git(repo, "diff", "--cached", "--binary", "--", "other.txt") == before
    assert (repo / "other.txt").read_text() == "also dirty\n"
    assert not git(repo, "diff", "HEAD", "--", "code.py", "new.py")
    assert git(repo, "cat-file", "-t", "refs/tags/experiment-v1").strip() == b"tag"
    metadata = json.loads(git(repo, "cat-file", "tag", "experiment-v1").split(b"\n\n", 1)[1])
    assert metadata["data_manifests"] == ["manifest.json"]
    assert "not captured" in metadata["limits"]


def test_clean_checkpoint_reuses_head_and_tag_is_idempotent(repo):
    head = git(repo, "rev-parse", "HEAD")
    run(repo)
    tag = git(repo, "rev-parse", "refs/tags/experiment-v1")
    assert git(repo, "rev-parse", "HEAD") == head
    assert "reused=true" in run(repo)
    assert git(repo, "rev-parse", "refs/tags/experiment-v1") == tag
    assert git(repo, "rev-list", "--count", "HEAD").strip() == b"1"
    assert git(repo, "diff", "--cached") == b""


def test_tag_collision_does_not_commit_or_change_index(repo):
    run(repo)
    before = git(repo, "rev-parse", "HEAD")
    (repo / "code.py").write_text("different\n")
    index = (repo / ".git/index").read_bytes()
    with pytest.raises(CheckpointError, match="tag already exists"):
        run(repo)
    assert git(repo, "rev-parse", "HEAD") == before
    assert (repo / ".git/index").read_bytes() == index
    assert not (repo / ".git/index.lock").exists()


@pytest.mark.parametrize(
    "unsafe",
    [
        "partial",
        "lock",
        "merge",
        "directory",
        "symlink",
        "traversal",
        "ignored",
        "raw-data",
        "detached",
        "lightweight",
    ],
)
def test_unsafe_states_fail_without_mutation(repo, unsafe):
    paths = ["code.py"]
    if unsafe == "partial":
        (repo / "code.py").write_text("staged\n")
        git(repo, "add", "code.py")
        (repo / "code.py").write_text("unstaged\n")
    elif unsafe == "lock":
        (repo / ".git/index.lock").touch()
    elif unsafe == "merge":
        (repo / ".git/MERGE_HEAD").write_bytes(git(repo, "rev-parse", "HEAD"))
    elif unsafe == "directory":
        paths = ["."]
    elif unsafe == "symlink":
        (repo / "link").symlink_to("code.py")
        paths = ["link"]
    elif unsafe == "traversal":
        paths = ["../code.py"]
    elif unsafe == "ignored":
        (repo / ".gitignore").write_text("secret\n")
        (repo / "secret").write_text("ignored\n")
        paths = ["secret"]
    elif unsafe == "raw-data":
        (repo / "data").mkdir()
        (repo / "data/raw.csv").write_text("payload\n")
        paths = ["data/raw.csv"]
    elif unsafe == "detached":
        git(repo, "checkout", "--detach", "-q")
    elif unsafe == "lightweight":
        git(repo, "tag", "experiment-v1")
    before = git(repo, "rev-parse", "HEAD")
    index = (repo / ".git/index").read_bytes()
    with pytest.raises(CheckpointError):
        run(repo, paths=paths)
    assert git(repo, "rev-parse", "HEAD") == before
    assert (repo / ".git/index").read_bytes() == index


@pytest.mark.parametrize("argument", ["--unknown", "--help"])
def test_cli_one_line_and_no_mutation_on_bad_arguments(repo, argument):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), argument], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert len(result.stderr.splitlines()) == 1
    assert result.stderr.startswith("ERROR ")
