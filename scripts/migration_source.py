"""Bounded, read-only migration discovery governed by the source .gitignore files."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, one_line, sha256_bytes

MAX_FILE_BYTES = 1024 * 1024
MAX_OUTPUT_CHARS = 6000
PAGE_SIZE = 40
PAYLOAD_DIRS = {
    "data",
    "datasets",
    "artifacts",
    "references",
    "results",
    "checkpoints",
    "runs",
}
ENVIRONMENT_DIRS = {"node_modules", "venv", "__pycache__"}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".cfg",
    ".ini",
    ".sh",
    ".ps1",
    ".bat",
}
TEXT_NAMES = {"license", "copying", "notice", "readme", "makefile", "dockerfile"}


def _restricted(parts: tuple[str, ...]) -> bool:
    return bool(parts and parts[0].lower() in PAYLOAD_DIRS) or any(
        (part.startswith(".") and part != ".gitignore") or part.lower() in ENVIRONMENT_DIRS
        for part in parts
    )


def _checked(source: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError("use an exact source-relative path without '..' or backslashes")
    if _restricted(path.parts):
        raise ValueError("hidden, environment and research payload paths need separate scope")
    current = source
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("symlinks are not migration inputs")
        if current.is_dir() and (current / ".git").exists():
            raise ValueError("nested repositories need their own source scope")
    return current


def _policy(source: Path, path: Path) -> str:
    root_policy = source / ".gitignore"
    if not root_policy.is_file() or root_policy.is_symlink():
        raise ValueError("source needs a regular .gitignore; do not assume unrestricted access")
    directory = path if path.is_dir() else path.parent
    for parent in (source, directory, *directory.parents):
        if not parent.is_relative_to(source):
            continue
        policy = parent / ".gitignore"
        if policy.is_symlink() or (policy.exists() and not policy.is_file()):
            raise ValueError("redirected .gitignore is not supported")
        if policy.exists() and policy.stat().st_size > 65536:
            raise ValueError(".gitignore exceeds the policy read budget")
    return sha256_bytes(root_policy.read_bytes())


def _ignored(source: Path, paths: list[Path]) -> set[str]:
    if not paths:
        return set()
    # An isolated Git directory avoids source Git config, tracked-file exemptions and global rules.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    with tempfile.TemporaryDirectory(prefix="migration-ignore-") as temporary:
        result = subprocess.run(
            ["git", "init", "--quiet", "--template=", temporary],
            env=env,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise ValueError("cannot initialize the isolated Git ignore checker")
        result = subprocess.run(
            [
                "git",
                f"--git-dir={temporary}/.git",
                f"--work-tree={source}",
                "-c",
                f"core.excludesFile={os.devnull}",
                "-c",
                "core.ignoreCase=false",
                "check-ignore",
                "--no-index",
                "-z",
                "--stdin",
            ],
            input=b"".join(os.fsencode(p.relative_to(source)) + b"\0" for p in paths),
            env=env,
            capture_output=True,
            check=False,
        )
        if result.returncode not in {0, 1} or result.stderr:
            raise ValueError("Git ignore checking failed; no source read is authorized")
        return {os.fsdecode(value) for value in result.stdout.split(b"\0") if value}


def inspect_source(
    source: Path,
    relative: str = ".",
    *,
    read: bool = False,
    offset: int = 0,
    start_line: int = 1,
    lines: int = 60,
    limit: int = PAGE_SIZE,
) -> dict:
    source = source.expanduser().absolute()
    if any(p.is_symlink() for p in (source, *source.parents)):
        raise ValueError("source must not use symlinks")
    source = source.resolve(strict=True)
    if not source.is_dir() or source == Path(source.anchor):
        raise ValueError("source must be a research directory, not a filesystem root")
    if source.is_relative_to(_REPO_ROOT) or _REPO_ROOT.is_relative_to(source):
        raise ValueError("source and template directories must not overlap")
    path = _checked(source, relative)
    policy_sha = _policy(source, path)
    if path not in (source, source / ".gitignore") and _ignored(source, [path]):
        raise ValueError("source .gitignore denies this path, even if Git tracks it")
    payload = {
        "source": str(source),
        "path": path.relative_to(source).as_posix(),
        "gitignore_sha256": policy_sha,
    }
    if read:
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("only regular text files may be read")
        if (
            path.name != ".gitignore"
            and path.suffix.lower() not in TEXT_SUFFIXES
            and path.name.lower() not in TEXT_NAMES
        ):
            raise ValueError("file type needs separate scope or a sanitized text export")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("source file exceeds the 1 MiB read budget")
        if start_line < 1 or not 1 <= lines <= 120:
            raise ValueError("use a positive start line and 1 to 120 lines")
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        if "\0" in text:
            raise ValueError("binary payloads are not migration text")
        content = text.splitlines(keepends=True)
        selected = content[start_line - 1 : start_line - 1 + lines]
        payload.update(
            sha256=sha256_bytes(raw),
            start_line=start_line,
            text="".join(selected),
            next_line=start_line + len(selected)
            if start_line - 1 + len(selected) < len(content)
            else None,
        )
    else:
        if not path.is_dir() or offset < 0 or not 1 <= limit <= PAGE_SIZE:
            raise ValueError("list requires a directory, nonnegative offset and limit 1 to 40")
        candidates = []
        for entry in sorted(path.iterdir()):
            name = entry.relative_to(source).as_posix()
            if entry.is_symlink():
                continue
            if _restricted(entry.relative_to(source).parts):
                continue
            if entry.is_dir() and (entry / ".git").exists():
                continue
            _checked(source, name)
            if entry.is_file() or entry.is_dir():
                candidates.append(entry)
        denied = _ignored(source, candidates)
        allowed = [p for p in candidates if p.relative_to(source).as_posix() not in denied]
        page = allowed[offset : offset + limit]
        payload.update(
            entries=[
                {
                    "path": p.relative_to(source).as_posix(),
                    "kind": "directory" if p.is_dir() else "file",
                }
                for p in page
            ],
            next_offset=offset + len(page) if offset + len(page) < len(allowed) else None,
        )
    if len(json.dumps(payload, ensure_ascii=True)) > MAX_OUTPUT_CHARS:
        raise ValueError("output exceeds 6000 characters; request fewer lines or narrower paths")
    return payload


def main(argv: list[str] | None = None) -> int:
    try:
        parser = QuietArgumentParser(description="Read-only, gitignore-aware migration discovery.")
        parser.add_argument("action", choices=["list", "read"])
        parser.add_argument("--source", required=True, type=Path)
        parser.add_argument("--path", default=".")
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--limit", type=int, default=PAGE_SIZE)
        parser.add_argument("--start-line", type=int, default=1)
        parser.add_argument("--lines", type=int, default=60)
        args = parser.parse_args(argv)
        payload = inspect_source(
            args.source,
            args.path,
            read=args.action == "read",
            offset=args.offset,
            start_line=args.start_line,
            lines=args.lines,
            limit=args.limit,
        )
        # JSON is single-line already; preserve indentation and spaces inside source excerpts.
        print("OK migration-source " + json.dumps(payload, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(
            f"ERROR migration-source: {type(exc).__name__}: {one_line(exc)[:400]}", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
