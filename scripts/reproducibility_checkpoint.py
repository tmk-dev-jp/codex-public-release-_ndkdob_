"""Create a scoped commit and immutable annotated reproducibility tag using native Git."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, run_script  # noqa: E402


class CheckpointError(ValueError):
    pass


def checkpoint(
    root: Path,
    tag: str,
    paths: list[str],
    configs: list[str],
    dependencies: list[str],
    manifests: list[str],
    message: str,
) -> str:
    root = root.resolve()
    env = os.environ.copy()
    # Explicit file names must never be interpreted as pathspec expressions.
    env["GIT_LITERAL_PATHSPECS"] = "1"

    def git(*args: str, data: bytes | None = None, index: str | None = None) -> bytes:
        local_env = env.copy()
        if index:
            local_env["GIT_INDEX_FILE"] = index
        result = subprocess.run(
            ["git", *args], cwd=root, env=local_env, input=data, capture_output=True
        )
        if result.returncode:
            raise CheckpointError(f"git {args[0]} failed; inspect repository state")
        return result.stdout

    if any(name in os.environ for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")):
        raise CheckpointError("unset Git repository/index environment overrides")
    if Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip()).resolve() != root:
        raise CheckpointError("run from the repository root")
    git("check-ref-format", f"refs/tags/{tag}")
    branch = git("symbolic-ref", "-q", "HEAD").decode().strip()
    head = git("rev-parse", "HEAD").decode().strip()
    git_dir = Path(os.fsdecode(git("rev-parse", "--absolute-git-dir")).strip())
    for marker in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "rebase-merge",
        "rebase-apply",
        "sequencer",
    ):
        if (git_dir / marker).exists():
            raise CheckpointError("finish the active Git operation first")
    if git("ls-files", "-u"):
        raise CheckpointError("resolve index conflicts first")
    selected = sorted(set(paths + configs + dependencies + manifests))
    if not paths or not configs or not dependencies or not manifests:
        raise CheckpointError("provide code, config, dependency and data-manifest paths")
    for name in selected:
        pure = PurePosixPath(name)
        if (
            not name
            or not pure.parts
            or pure.is_absolute()
            or str(pure) != name
            or ".." in pure.parts
            or any(ord(char) < 32 for char in name)
            or pure.parts[0] == ".git"
        ):
            raise CheckpointError("paths must be explicit repository-relative file names")
        path = root / name
        if path.resolve() != path or not path.is_file() or path.is_symlink():
            raise CheckpointError(f"path must be an existing regular file: {name}")
        if pure.parts[0] in {"artifacts", "references"} or (
            pure.parts[0] == "data" and name != "data/MANIFEST.json"
        ):
            raise CheckpointError("raw data, artifacts and reference payloads are excluded")
        # Full-file selection cannot silently destroy an intentionally partial stage.
        staged = git("diff", "--cached", "--name-only", "--", name)
        unstaged = git("diff", "--name-only", "--", name)
        if staged and unstaged:
            raise CheckpointError(f"selected path is partially staged: {name}")
    metadata = {
        "schema_version": 1,
        "code": sorted(set(paths)),
        "configs": sorted(set(configs)),
        "dependencies": sorted(set(dependencies)),
        "data_manifests": sorted(set(manifests)),
        "limits": (
            "External data and the installed environment are not captured; "
            "verify manifest identities and install the recorded dependencies."
        ),
    }
    annotation = json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n"
    index_path = Path(os.fsdecode(git("rev-parse", "--git-path", "index")).strip())
    if not index_path.is_absolute():
        index_path = root / index_path
    lock_path = index_path.with_name(index_path.name + ".lock")
    # Git's own index lock prevents cooperating writers throughout preparation.
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError as exc:
        raise CheckpointError("Git index is locked") from exc
    os.close(lock_fd)
    try:
        with tempfile.TemporaryDirectory(prefix="repro-checkpoint-") as temporary:
            temporary_index = str(Path(temporary) / "index")
            git("read-tree", head, index=temporary_index)
            git("add", "--", *selected, index=temporary_index)
            tree = git("write-tree", index=temporary_index).decode().strip()
            tag_ref = f"refs/tags/{tag}"
            existing = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", tag_ref],
                cwd=root,
                env=env,
                capture_output=True,
            )
            if existing.returncode == 0:
                if (
                    git("cat-file", "-t", tag_ref).strip() == b"tag"
                    and git("rev-parse", f"{tag_ref}^{{commit}}").decode().strip() == head
                    and git("rev-parse", f"{tag_ref}^{{tree}}").decode().strip() == tree
                    and git("cat-file", "tag", tag_ref).split(b"\n\n", 1)[1] == annotation.encode()
                ):
                    return f"commit={head} tag={tag} reused=true"
                raise CheckpointError(
                    "tag already exists with a different checkpoint; choose a new tag"
                )
            if existing.returncode != 1:
                raise CheckpointError("could not inspect tag")
            commit = head
            if tree != git("rev-parse", "HEAD^{tree}").decode().strip():
                commit = (
                    git("commit-tree", tree, "-p", head, data=(message + "\n").encode())
                    .decode()
                    .strip()
                )
            identity = git("var", "GIT_COMMITTER_IDENT").decode().strip()
            tag_object = (
                f"object {commit}\ntype commit\ntag {tag}\ntagger {identity}\n\n{annotation}"
            )
            tag_hash = git("mktag", data=tag_object.encode()).decode().strip()
            # Prepare the replacement real index, preserving every unrelated entry.
            replacement = str(Path(temporary) / "replacement")
            if index_path.exists():
                shutil.copyfile(index_path, replacement)
            else:
                git("read-tree", head, index=replacement)
            git("reset", "-q", commit, "--", *selected, index=replacement)
            shutil.copyfile(replacement, lock_path)
            transaction = (
                f"start\nupdate {branch} {commit} {head}\n"
                f"create {tag_ref} {tag_hash}\nprepare\ncommit\n"
            )
            git("update-ref", "--stdin", data=transaction.encode())
            os.replace(lock_path, index_path)
            return f"commit={commit} tag={tag} reused=false"
    finally:
        lock_path.unlink(missing_ok=True)


def _execute() -> str:
    parser = QuietArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--dependency", action="append", required=True)
    parser.add_argument("--data-manifest", action="append", required=True)
    parser.add_argument("--message", default="Record reproducible experiment inputs")
    args = parser.parse_args()
    return checkpoint(
        Path.cwd(),
        args.tag,
        args.path,
        args.config,
        args.dependency,
        args.data_manifest,
        args.message,
    )


if __name__ == "__main__":
    raise SystemExit(run_script("checkpoint-reproducibility", _execute))
