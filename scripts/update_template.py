"""Conservatively update reusable files from public GitHub tags or local Git refs."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, root_from_script, run_script  # noqa: E402

ROOT_FILES = ("AGENTS.md", "README.md", "TREE.txt", "Makefile", "pyproject.toml", ".gitignore")
PREFIXES = (
    "scripts/",
    "schemas/",
    "tests/unit/",
    ".agents/skills/",
    "src/dl_research/",
    "human/",
    "configs/templates/",
    "experiments/templates/",
)
MAX_BYTES = 32 * 1024 * 1024


def git(repo: Path, *args: str, public: bool = False) -> bytes:
    if any(
        key.startswith("GIT_") and key not in {"GIT_PAGER", "GIT_TERMINAL_PROMPT"}
        for key in os.environ
    ):
        raise ValueError("unset GIT_* environment overrides before updating")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if public:
        # Public HTTPS only: no configured credential helpers, URL rewrites or prompts.
        env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_ASKPASS="",
            SSH_ASKPASS="",
        )
    result = subprocess.run(
        ["git", "--literal-pathspecs", "--no-optional-locks", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        env=env,
        timeout=120 if public else None,
    )
    if result.returncode:
        raise ValueError(
            "Git command failed: " + result.stderr.decode(errors="replace").strip()[:240]
        )
    return result.stdout


def managed(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return (
        bool(parts)
        and not name.startswith("/")
        and ".." not in parts
        and "\\" not in name
        and not any(
            part in {".git", ".venv", "venv", "__pycache__", "node_modules"}
            or part == ".env"
            or part.startswith(".env.")
            for part in parts
        )
        and all(not any(ord(char) < 32 for char in part) for part in parts)
        and (name in ROOT_FILES or name.startswith(PREFIXES))
    )


def tree(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    result = {}
    for entry in git(repo, "ls-tree", "-rz", commit, "--", *ROOT_FILES, *PREFIXES).split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        name = raw_name.decode("utf-8")
        if not managed(name):
            continue
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"unsupported template path or mode: {name}")
        result[name] = (mode, blob)
    return result


def local_path(root: Path, name: str) -> Path:
    path = root / name
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise ValueError(f"symlinked destination: {name}")
        if candidate != path and candidate.exists() and not candidate.is_dir():
            raise ValueError(f"destination ancestor is not a directory: {name}")
    if path.exists() and not path.is_file():
        raise ValueError(f"destination is not a regular file: {name}")
    return path


def content(repo: Path, entry: tuple[str, str] | None) -> bytes | None:
    if entry is None:
        return None
    size = int(git(repo, "cat-file", "-s", entry[1]))
    if size > MAX_BYTES:
        raise ValueError("template file exceeds 32 MiB")
    return git(repo, "cat-file", "blob", entry[1])


def matches(path: Path, payload: bytes | None, mode: str | None, executable: bool) -> bool:
    if payload is None:
        return not path.exists()
    return (
        path.is_file()
        and path.stat().st_size == len(payload)
        and path.read_bytes() == payload
        and (not executable or bool(path.stat().st_mode & stat.S_IXUSR) == (mode == "100755"))
    )


def replace_file(path: Path, payload: bytes | None, mode: int) -> None:
    if payload is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".template-update-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def update(args) -> str:
    github = getattr(args, "github", None)
    if not github:
        return update_local(args)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", github):
        raise ValueError("--github must be OWNER/REPO on public github.com")
    if github.split("/")[1] in {".", ".."}:
        raise ValueError("--github requires a repository name")
    with tempfile.TemporaryDirectory(prefix="template-github-") as temporary:
        source = Path(temporary)
        for tag in (args.from_ref, args.to_ref):
            if not tag or tag.startswith(("-", "refs/")):
                raise ValueError("provide exact tag names without refs/tags/")
            git(source, "check-ref-format", f"refs/tags/{tag}")
        git(source, "init", "--bare", "--quiet", public=True)
        refs = sorted({f"refs/tags/{args.from_ref}", f"refs/tags/{args.to_ref}"})
        git(
            source,
            "fetch", "--quiet", "--depth=1", "--no-tags", "--no-recurse-submodules",
            f"https://github.com/{github}.git",
            *(f"{ref}:{ref}" for ref in refs),
            public=True,
        )
        local = SimpleNamespace(**vars(args))
        local.template = str(source)
        local.from_ref = f"refs/tags/{args.from_ref}"
        local.to_ref = f"refs/tags/{args.to_ref}"
        return update_local(local) + f" github={github}"


def update_local(args) -> str:
    root = Path(args.root).resolve()
    source = Path(args.template).resolve()
    if Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise ValueError("destination must be a Git worktree root")
    old = (
        git(source, "rev-parse", "--verify", "--end-of-options", args.from_ref + "^{commit}")
        .decode()
        .strip()
    )
    new = (
        git(source, "rev-parse", "--verify", "--end-of-options", args.to_ref + "^{commit}")
        .decode()
        .strip()
    )
    before, after = tree(source, old), tree(source, new)
    selected = args.path
    if selected and any(not managed(name) for name in selected):
        raise ValueError("explicit paths must belong to the reusable template allowlist")
    names = sorted(
        name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
    )
    if selected:
        if any(name not in before and name not in after for name in selected):
            raise ValueError("explicit path absent from both template commits")
        names = [name for name in names if name in selected]
    staged = set(git(root, "diff", "--cached", "--name-only", "-z").decode().split("\0"))
    tracked = (
        set(git(root, "ls-files", "-z", "--", *names).decode().split("\0")) if names else set()
    )
    executable = (
        git(root, "config", "--default", "true", "--bool", "core.filemode").strip() != b"false"
    )
    changes = []
    conflicts = []
    total = 0
    for name in names:
        path = local_path(root, name)
        previous, target = content(source, before.get(name)), content(source, after.get(name))
        total += len(previous or b"") + len(target or b"")
        if total > MAX_BYTES:
            raise ValueError("update exceeds 32 MiB; select a smaller explicit path set")
        previous_mode = before[name][0] if name in before else None
        target_mode = after[name][0] if name in after else None
        if name in staged:
            conflicts.append(name)
        elif matches(path, target, target_mode, executable):
            continue
        elif path.exists() and name not in tracked:
            conflicts.append(name)
        elif not matches(path, previous, previous_mode, executable):
            conflicts.append(name)
        else:
            changes.append(
                (
                    name,
                    target,
                    target_mode,
                    previous,
                    stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
                )
            )
    if conflicts:
        raise ValueError(f"local/index conflicts ({len(conflicts)}): " + ", ".join(conflicts[:5]))
    plan = {
        "from_commit": old,
        "to_commit": new,
        "changes": [
            {
                "path": name,
                "action": "delete" if target is None else "add" if previous is None else "update",
            }
            for name, target, _, previous, _ in changes
        ],
    }
    if getattr(args, "github", None):
        plan.update(
            repository=f"https://github.com/{args.github}",
            from_tag=args.from_ref.removeprefix("refs/tags/"),
            to_tag=args.to_ref.removeprefix("refs/tags/"),
        )
    if args.plan:
        plan_path = Path(args.plan).resolve()
        if plan_path.is_relative_to(root) or plan_path.is_relative_to(source):
            raise ValueError("plan output must be outside template and destination repositories")
        with plan_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(plan, indent=2) + "\n")
    backup = None
    if args.apply and changes:
        backup = Path(tempfile.mkdtemp(prefix="template-update-backup-"))
        (backup / "plan.json").write_text(
            json.dumps({**plan, "destination": str(root)}, indent=2) + "\n"
        )
        for name, _, _, previous, previous_mode in changes:
            if previous is not None:
                saved = backup / "files" / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(previous)
                os.chmod(saved, previous_mode)
        completed = False
        try:
            for name, target, mode, _, _ in changes:
                replace_file(root / name, target, 0o755 if mode == "100755" else 0o644)
            completed = True
        finally:
            if not completed:
                for name, _, _, previous, previous_mode in reversed(changes):
                    replace_file(root / name, previous, previous_mode or 0o644)
    return f"{'applied' if args.apply else 'preview'} files={len(changes)} from={old} to={new}" + (
        f" backup={backup}" if backup else ""
    )


def main() -> int:
    def action() -> str:
        parser = QuietArgumentParser()
        parser.add_argument("--root", default=str(root_from_script()))
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument("--github")
        source.add_argument("--template")
        parser.add_argument("--from-tag", "--from-ref", dest="from_ref", required=True)
        parser.add_argument("--to-tag", "--to-ref", dest="to_ref", required=True)
        parser.add_argument("--path", action="append")
        parser.add_argument("--plan")
        parser.add_argument("--apply", action="store_true")
        return update(parser.parse_args())

    return run_script("update_template", action)


if __name__ == "__main__":
    raise SystemExit(main())
