"""Experiment scope validation shared by planning gates and audits."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.common import normalized_unique_paths, safe_relative_path

PATH_KEYS = ("read_paths", "write_paths", "test_paths")
CHANGE_ROLES = {"intervention", "support", "verification"}
CHANGE_ACTIONS = {"create", "modify"}
PYTHON_SYMBOL = re.compile(
    r"(?:[A-Za-z_][A-Za-z0-9_]*)(?:\.[A-Za-z_][A-Za-z0-9_]*)*|<module>"
)


def _normalize_change_targets(
    scope: dict[str, Any],
    write_paths: list[str],
    test_paths: list[str],
) -> list[dict[str, Any]]:
    overlap = set(write_paths) & set(test_paths)
    if overlap:
        raise ValueError(f"write_paths and test_paths overlap: {sorted(overlap)[0]}")
    declared_paths = set(write_paths) | set(test_paths)
    values = scope.get("change_targets")
    if not isinstance(values, list):
        raise ValueError("SCOPE.json change_targets must be a list")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "role",
            "action",
            "symbols",
        }:
            raise ValueError(
                "change_targets entries require only path, role, action, and symbols"
            )
        path_value = item.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError("change target path must be a non-empty string")
        path_value = Path(path_value).as_posix()
        if path_value in seen:
            raise ValueError(f"duplicate change target: {path_value}")
        if path_value not in declared_paths:
            raise ValueError(f"change target is outside write/test paths: {path_value}")

        role = item.get("role")
        action = item.get("action")
        symbols = item.get("symbols")
        if role not in CHANGE_ROLES:
            raise ValueError(f"invalid change target role: {path_value}")
        if action not in CHANGE_ACTIONS:
            raise ValueError(f"invalid change target action: {path_value}")
        if not isinstance(symbols, list) or not symbols:
            raise ValueError(f"change target symbols must be non-empty: {path_value}")
        if any(not isinstance(symbol, str) or not symbol for symbol in symbols):
            raise ValueError(f"invalid change target symbol: {path_value}")
        if len(symbols) != len(set(symbols)):
            raise ValueError(f"duplicate change target symbol: {path_value}")
        if Path(path_value).suffix == ".py":
            if any(PYTHON_SYMBOL.fullmatch(symbol) is None for symbol in symbols):
                raise ValueError(f"invalid Python target symbol: {path_value}")
        elif symbols != ["<file>"]:
            raise ValueError(
                f"non-Python change target must declare only <file>: {path_value}"
            )
        if path_value in test_paths and role != "verification":
            raise ValueError(f"test target must use verification role: {path_value}")
        if path_value in write_paths and role == "verification":
            raise ValueError(f"write target cannot use verification role: {path_value}")
        seen.add(path_value)
        normalized.append(
            {
                "path": path_value,
                "role": role,
                "action": action,
                "symbols": symbols,
            }
        )

    missing = declared_paths - seen
    if missing:
        raise ValueError(f"change target missing for path: {sorted(missing)[0]}")
    if seen - declared_paths:
        raise ValueError("change target paths differ from write/test paths")
    if write_paths and not any(item["role"] == "intervention" for item in normalized):
        raise ValueError("write targets require at least one intervention role")
    return normalized


def _normalize_reasoned_python_reads(
    root: Path,
    scope: dict[str, Any],
    *,
    key: str,
    item_label: str,
    budget_label: str,
    scope_paths: list[str],
    maximum: int,
) -> list[dict[str, str]]:
    reads = scope.get(key)
    if not isinstance(reads, list):
        raise ValueError(f"SCOPE.json {key} must be a list")
    normalized_reads: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in reads:
        if not isinstance(item, dict) or set(item) != {"path", "reason"}:
            raise ValueError(f"{key} entries require only path and reason")
        path_value = item.get("path")
        reason = item.get("reason")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError(f"{item_label} path must be a non-empty string")
        path_value = Path(path_value).as_posix()
        if path_value in seen:
            raise ValueError(f"duplicate {item_label}: {path_value}")
        if path_value not in scope_paths:
            raise ValueError(
                f"{item_label} must also be an implementation scope path: "
                f"{path_value}"
            )
        path = safe_relative_path(root, path_value)
        if path.suffix != ".py" or not path.is_file():
            raise ValueError(
                f"{item_label} must name an existing Python file: {path_value}"
            )
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or reason.strip().lower() in {"none", "pending"}
            or reason.lstrip().startswith("<")
        ):
            raise ValueError(f"{item_label} requires a filled reason: {path_value}")
        seen.add(path_value)
        normalized_reads.append({"path": path_value, "reason": reason.strip()})
    if len(normalized_reads) > maximum:
        raise ValueError(
            f"{budget_label} exceed maximum {maximum}: {len(normalized_reads)}"
        )
    return normalized_reads


def validate_scope(
    root: Path,
    scope: dict[str, Any],
    *,
    maximum_files: int,
    maximum_planning_python_reads: int,
    maximum_implementation_entry_python_reads: int,
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(scope, dict):
        raise ValueError("SCOPE.json must be an object")
    normalized_scope = dict(scope)
    all_paths: list[str] = []
    for key in PATH_KEYS:
        values = scope.get(key)
        if not isinstance(values, list):
            raise ValueError(f"SCOPE.json {key} must be a list")
        normalized = normalized_unique_paths(values)
        normalized_scope[key] = normalized
        for value in normalized:
            if any(token in value for token in ("*", "?", "[")):
                raise ValueError(f"scope glob is prohibited: {value}")
            path = safe_relative_path(root, value, allow_missing=key != "read_paths")
            if path.exists() and not path.is_file():
                raise ValueError(f"scope paths must name files, not directories: {value}")
        all_paths.extend(normalized)

    unique_paths = list(dict.fromkeys(all_paths))
    if len(unique_paths) > maximum_files:
        raise ValueError(
            f"scope contains {len(unique_paths)} files; maximum is {maximum_files}"
        )

    normalized_scope["change_targets"] = _normalize_change_targets(
        scope,
        normalized_scope["write_paths"],
        normalized_scope["test_paths"],
    )

    normalized_scope["planning_reads"] = _normalize_reasoned_python_reads(
        root,
        scope,
        key="planning_reads",
        item_label="planning read",
        budget_label="planning Python reads",
        scope_paths=unique_paths,
        maximum=maximum_planning_python_reads,
    )
    normalized_scope["implementation_entry_reads"] = (
        _normalize_reasoned_python_reads(
            root,
            scope,
            key="implementation_entry_reads",
            item_label="implementation entry read",
            budget_label="implementation entry Python reads",
            scope_paths=unique_paths,
            maximum=maximum_implementation_entry_python_reads,
        )
    )
    return normalized_scope, unique_paths
