"""Shared one-line output, atomic-file, hashing, and path helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any


class QuietArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        raise ValueError(message)


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def one_line(value: object) -> str:
    return " ".join(str(value).split())


def run_script(name: str, action: Callable[[], str]) -> int:
    try:
        result = one_line(action())
        print(f"OK {name} {result}".rstrip())
        return 0
    except Exception as exc:
        message = one_line(exc)[:400]
        print(f"ERROR {name}: {type(exc).__name__}: {message}", file=sys.stderr)
        return 1


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def safe_relative_path(root: Path, value: str, *, allow_missing: bool = False) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"path must be repository-relative without '..': {value}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path leaves repository: {value}") from exc
    if not allow_missing and not resolved.exists():
        raise FileNotFoundError(f"path not found: {value}")
    return resolved


def normalized_unique_paths(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("scope paths must be non-empty strings")
        value = Path(raw).as_posix()
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def sha256_path_set(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    normalized = sorted(normalized_unique_paths(paths))
    for value in normalized:
        path = safe_relative_path(root, value)
        if not path.is_file():
            raise ValueError(f"implementation path must be a file: {value}")
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
