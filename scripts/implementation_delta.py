"""Lock and verify the declared implementation delta for one experiment."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.common import (
    atomic_write_json,
    read_json,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)
from scripts.records import field, section

DELTA_FILENAME = "IMPLEMENTATION_DELTA.json"
PLAN_FIELDS = (
    "Baseline behavior",
    "Candidate behavior",
    "Intervention point",
    "Unchanged invariants",
)
IGNORED_WORKSPACE_PREFIXES = (
    "artifacts/",
    "data/raw/",
    "data/processed/",
    "experiments/active/",
    "experiments/completed/",
    "references/inbox/",
    "references/originals/",
    "review/",
)
IGNORED_WORKSPACE_PATHS = {
    "experiments/INDEX.json",
    "research/CONTEXT.md",
    "research/STATE.json",
    "research/TRAINING_CONTROLS.json",
}


class ImplementationDeltaRequiredError(ValueError):
    pass


def _payload_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def _semantic_plan(record_text: str) -> dict[str, str]:
    method = section(record_text, "## Method")
    return {
        label.lower().replace(" ", "_"): field(method, label)
        for label in PLAN_FIELDS
    }


def _symbol_fingerprints(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot inspect Python symbols in {path}") from exc

    result: dict[str, str] = {}
    module_nodes: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = _payload_hash(ast.dump(node, include_attributes=False))
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result[f"{node.name}.{child.name}"] = _payload_hash(
                            ast.dump(child, include_attributes=False)
                        )
        else:
            module_nodes.append(node)
    if module_nodes:
        result["<module>"] = _payload_hash(
            [ast.dump(node, include_attributes=False) for node in module_nodes]
        )
    return result


def _file_state(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    path_value = target["path"]
    path = safe_relative_path(root, path_value, allow_missing=True)
    exists = path.is_file()
    state: dict[str, Any] = {
        "exists": exists,
        "sha256": sha256_file(path) if exists else None,
    }
    if path.suffix == ".py" and exists:
        state["symbols"] = _symbol_fingerprints(path)
    else:
        state["symbols"] = {}
    return state


def _observed_change(before: dict[str, Any], after: dict[str, Any]) -> str:
    if not before["exists"] and after["exists"]:
        return "create"
    if before["exists"] and after["exists"] and before["sha256"] != after["sha256"]:
        return "modify"
    return "unchanged"


def _undeclared_symbols(changed: list[str], declared: list[str]) -> list[str]:
    if "<file>" in declared:
        return []
    return [
        symbol
        for symbol in changed
        if not any(
            symbol == expected
            or symbol.startswith(f"{expected}.")
            or expected.startswith(f"{symbol}.")
            for expected in declared
        )
    ]


def _git_output(
    root: Path,
    arguments: list[str],
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        return None


def _status_paths(payload: bytes) -> list[tuple[str, str]]:
    tokens = payload.split(b"\0")
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4:
            raise ValueError("unexpected git status entry")
        status = token[:2].decode("ascii", errors="replace")
        path = token[3:].decode("utf-8", errors="surrogateescape")
        result.append((status, Path(path).as_posix()))
        if "R" in status or "C" in status:
            if index >= len(tokens) or not tokens[index]:
                raise ValueError("incomplete git rename status")
            source = tokens[index].decode("utf-8", errors="surrogateescape")
            index += 1
            result.append((status, Path(source).as_posix()))
    return result


def _workspace_ignored(path: str, targets: set[str], config_path: str) -> bool:
    parts = Path(path).parts
    if (
        "__pycache__" in parts
        or ".pytest_cache" in parts
        or "htmlcov" in parts
        or path == ".coverage"
        or path.startswith(".coverage.")
        or path.endswith(".pyc")
    ):
        return True
    if path in targets or path == config_path or path in IGNORED_WORKSPACE_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in IGNORED_WORKSPACE_PREFIXES)


def _workspace_snapshot(
    root: Path,
    targets: set[str],
    config_path: str,
) -> dict[str, Any]:
    top = _git_output(root, ["rev-parse", "--show-toplevel"])
    head = _git_output(root, ["rev-parse", "--verify", "HEAD"])
    status = _git_output(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    if (
        top is None
        or head is None
        or status is None
        or top.returncode != 0
        or head.returncode != 0
        or status.returncode != 0
    ):
        return {"mode": "scope_only", "reason": "git_head_unavailable"}
    git_root = Path(top.stdout.decode("utf-8").strip()).resolve()
    if git_root != root.resolve():
        return {"mode": "scope_only", "reason": "repository_root_differs"}

    entries: list[dict[str, Any]] = []
    for git_status, path_value in _status_paths(status.stdout):
        if _workspace_ignored(path_value, targets, config_path):
            continue
        path = safe_relative_path(root, path_value, allow_missing=True)
        entries.append(
            {
                "path": path_value,
                "status": git_status,
                "exists": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    entries.sort(key=lambda item: (item["path"], item["status"]))
    return {
        "mode": "git_status",
        "head": head.stdout.decode("ascii").strip(),
        "state_sha256": _payload_hash(entries),
        "dirty_paths": len(entries),
    }


def _metadata(root: Path, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "declared_sha256": _payload_hash(_declared_material(payload)),
        "status": payload["status"],
        "workspace_mode": payload["workspace_guard"]["before"]["mode"],
    }


def _declared_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "experiment_id": payload.get("experiment_id"),
        "plan": payload.get("plan"),
        "targets": [
            {
                **{
                    key: target[key]
                    for key in ("path", "role", "action", "symbols")
                },
                "before": target["before"],
            }
            for target in payload.get("targets", [])
        ],
        "workspace_before": payload.get("workspace_guard", {}).get("before"),
    }


def _target_declarations(scope: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "path": item["path"],
            "role": item["role"],
            "action": item["action"],
            "symbols": item["symbols"],
        }
        for item in scope["change_targets"]
    ]


def lock_implementation_delta(
    root: Path,
    experiment_id: str,
    record_text: str,
    scope: dict[str, Any],
    config_path: str,
) -> tuple[Path, dict[str, Any]]:
    targets = _target_declarations(scope)
    locked_targets = []
    for target in targets:
        before = _file_state(root, target)
        if target["action"] == "create" and before["exists"]:
            raise ValueError(f"create target already exists: {target['path']}")
        if target["action"] == "modify" and not before["exists"]:
            raise ValueError(f"modify target does not exist: {target['path']}")
        locked_targets.append({**target, "before": before, "after": None})

    target_paths = {item["path"] for item in targets}
    payload = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "status": "locked",
        "plan": _semantic_plan(record_text),
        "targets": locked_targets,
        "workspace_guard": {
            "before": _workspace_snapshot(root, target_paths, config_path),
            "after": None,
        },
    }
    path = root / "experiments/active" / experiment_id / DELTA_FILENAME
    atomic_write_json(path, payload)
    return path, _metadata(root, path, payload)


def _load_delta(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
    expected_status: str,
) -> tuple[Path, dict[str, Any]]:
    metadata = manifest.get("implementation_delta")
    path = active / DELTA_FILENAME
    if not isinstance(metadata, dict) or not path.is_file():
        raise ImplementationDeltaRequiredError("implementation delta is required")
    if metadata.get("sha256") != sha256_file(path):
        raise ImplementationDeltaRequiredError("implementation delta changed")
    payload = read_json(path)
    if metadata.get("declared_sha256") != _payload_hash(
        _declared_material(payload)
    ):
        raise ImplementationDeltaRequiredError(
            "declared implementation delta changed"
        )
    if (
        payload.get("experiment_id") != manifest.get("id")
        or payload.get("status") != expected_status
        or metadata.get("status") != expected_status
    ):
        raise ImplementationDeltaRequiredError(
            f"implementation delta must be {expected_status}"
        )
    return path, payload


def _require_plan_matches(
    active: Path,
    payload: dict[str, Any],
    scope: dict[str, Any],
) -> None:
    record = (active / "EXPERIMENT.md").read_text(encoding="utf-8")
    if payload.get("plan") != _semantic_plan(record):
        raise ImplementationDeltaRequiredError("implementation delta plan changed")
    declarations = _target_declarations(scope)
    recorded = [
        {key: target[key] for key in ("path", "role", "action", "symbols")}
        for target in payload.get("targets", [])
    ]
    if recorded != declarations:
        raise ImplementationDeltaRequiredError("implementation delta targets changed")


def declared_implementation_delta_hash(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
) -> str:
    metadata = manifest.get("implementation_delta")
    path = active / DELTA_FILENAME
    if not isinstance(metadata, dict) or not path.is_file():
        raise ImplementationDeltaRequiredError("implementation delta is required")
    if metadata.get("sha256") != sha256_file(path):
        raise ImplementationDeltaRequiredError("implementation delta changed")
    payload = read_json(path)
    declared_hash = _payload_hash(_declared_material(payload))
    if metadata.get("declared_sha256") != declared_hash:
        raise ImplementationDeltaRequiredError(
            "declared implementation delta changed"
        )
    if payload.get("experiment_id") != manifest.get("id") or payload.get(
        "status"
    ) != metadata.get("status"):
        raise ImplementationDeltaRequiredError("implementation delta metadata differs")
    _require_plan_matches(active, payload, read_json(active / "SCOPE.json"))
    return declared_hash


def require_locked_implementation_delta(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _, payload = _load_delta(root, active, manifest, "locked")
    scope = read_json(active / "SCOPE.json")
    _require_plan_matches(active, payload, scope)
    targets = {target["path"] for target in payload["targets"]}
    for target in payload["targets"]:
        if _file_state(root, target) != target["before"]:
            raise ImplementationDeltaRequiredError(
                f"implementation target changed before delegation: {target['path']}"
            )
    current = _workspace_snapshot(root, targets, manifest["config"])
    if current != payload["workspace_guard"]["before"]:
        raise ImplementationDeltaRequiredError(
            "unscoped workspace changed before implementation"
        )
    return payload


def complete_implementation_delta(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
    *,
    repair: bool = False,
) -> tuple[Path, dict[str, Any]]:
    expected_status = "implemented" if repair else "locked"
    path, payload = _load_delta(root, active, manifest, expected_status)
    scope = read_json(active / "SCOPE.json")
    _require_plan_matches(active, payload, scope)
    target_paths = {target["path"] for target in payload["targets"]}
    current_workspace = _workspace_snapshot(root, target_paths, manifest["config"])
    workspace_key = "after" if repair else "before"
    if current_workspace != payload["workspace_guard"][workspace_key]:
        raise ImplementationDeltaRequiredError(
            "undeclared workspace change detected during implementation or repair"
        )

    completed_targets = []
    repair_targets = []
    for target in payload["targets"]:
        after = _file_state(root, target)
        if not after["exists"]:
            raise ImplementationDeltaRequiredError(
                f"implementation target is missing: {target['path']}"
            )
        prior = target.get("after") if repair else target["before"]
        if not isinstance(prior, dict):
            raise ImplementationDeltaRequiredError("repair baseline is missing")
        observed_change = _observed_change(prior, after)
        changed = observed_change != "unchanged"
        if not repair and observed_change != target["action"]:
            raise ImplementationDeltaRequiredError(
                f"implementation target action differs: {target['path']} "
                f"expected={target['action']} observed={observed_change}"
            )
        before_symbols = prior.get("symbols", {})
        after_symbols = after.get("symbols", {})
        changed_symbols = sorted(
            name
            for name in set(before_symbols) | set(after_symbols)
            if before_symbols.get(name) != after_symbols.get(name)
        )
        for symbol in target["symbols"]:
            if symbol == "<file>":
                continue
            if symbol not in after_symbols:
                raise ImplementationDeltaRequiredError(
                    f"declared symbol is missing after implementation: {symbol}"
                )
            if not repair and symbol not in changed_symbols:
                raise ImplementationDeltaRequiredError(
                    f"declared symbol did not change: {symbol}"
                )
        undeclared_symbols = _undeclared_symbols(
            changed_symbols,
            target["symbols"],
        )
        if undeclared_symbols:
            raise ImplementationDeltaRequiredError(
                f"undeclared symbol changed in {target['path']}: "
                f"{undeclared_symbols[0]}"
            )
        completed = {**target, "after": after}
        if not repair:
            completed["observed_changed_symbols"] = changed_symbols
            completed["observed_change"] = observed_change
        completed_targets.append(completed)
        if repair and changed:
            repair_targets.append(
                {
                    "path": target["path"],
                    "before_sha256": prior["sha256"],
                    "after_sha256": after["sha256"],
                    "observed_change": observed_change,
                    "changed_symbols": changed_symbols,
                }
            )

    if repair:
        if not repair_targets:
            raise ImplementationDeltaRequiredError("repair changed no declared target")
        repairs = payload.setdefault("repairs", [])
        repairs.append({"sequence": len(repairs) + 1, "targets": repair_targets})

    payload["targets"] = completed_targets
    payload["workspace_guard"]["after"] = current_workspace
    payload["status"] = "implemented"
    atomic_write_json(path, payload)
    return path, _metadata(root, path, payload)


def require_current_implementation_delta(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _, payload = _load_delta(root, active, manifest, "implemented")
    scope = read_json(active / "SCOPE.json")
    _require_plan_matches(active, payload, scope)
    target_paths = {target["path"] for target in payload["targets"]}
    for target in payload["targets"]:
        if _file_state(root, target) != target["after"]:
            raise ImplementationDeltaRequiredError(
                f"implemented target changed after recording: {target['path']}"
            )
    current = _workspace_snapshot(root, target_paths, manifest["config"])
    if current != payload["workspace_guard"]["after"]:
        raise ImplementationDeltaRequiredError(
            "undeclared workspace change detected after implementation"
        )
    return payload


def compact_implementation_delta(payload: dict[str, Any]) -> dict[str, Any]:
    targets = []
    for target in payload.get("targets", []):
        targets.append(
            {
                "path": target["path"],
                "role": target["role"],
                "action": target["action"],
                "declared_symbols": target["symbols"],
                "before_sha256": target["before"]["sha256"],
                "after_sha256": (target.get("after") or {}).get("sha256"),
                "observed_change": target.get("observed_change"),
                "observed_changed_symbols": target.get(
                    "observed_changed_symbols", []
                ),
            }
        )
    before_workspace = payload.get("workspace_guard", {}).get("before")
    after_workspace = payload.get("workspace_guard", {}).get("after")
    return {
        "schema_version": payload.get("schema_version"),
        "experiment_id": payload.get("experiment_id"),
        "status": payload.get("status"),
        "plan": payload.get("plan"),
        "targets": targets,
        "repair_count": len(payload.get("repairs", [])),
        "workspace_guard": {
            "mode": payload.get("workspace_guard", {})
            .get("before", {})
            .get("mode"),
            "unchanged_outside_targets": (
                None
                if after_workspace is None
                else before_workspace == after_workspace
            ),
        },
    }
