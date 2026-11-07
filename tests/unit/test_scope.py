from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.scope import validate_scope


def test_scope_template_starts_without_python_phase_reads() -> None:
    payload = json.loads(
        Path("experiments/templates/SCOPE.json").read_text(encoding="utf-8")
    )

    normalized, _ = validate_scope(
        Path.cwd(),
        payload,
        maximum_files=10,
        maximum_planning_python_reads=3,
        maximum_implementation_entry_python_reads=3,
    )

    assert payload["schema_version"] == "1.3"
    assert normalized["change_targets"] == []
    assert normalized["planning_reads"] == []
    assert normalized["implementation_entry_reads"] == []


def _python_files(root: Path, count: int) -> list[str]:
    paths: list[str] = []
    for index in range(count):
        relative = f"src/module_{index}.py"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"VALUE = {index}\n", encoding="utf-8")
        paths.append(relative)
    return paths


def _scope(paths: list[str]) -> dict:
    return {
        "read_paths": [],
        "write_paths": paths,
        "test_paths": [],
        "change_targets": [
            {
                "path": path,
                "role": "intervention",
                "action": "modify",
                "symbols": ["<module>"],
            }
            for path in paths
        ],
        "planning_reads": [
            {"path": path, "reason": "Confirm the exact integration point."}
            for path in paths
        ],
        "implementation_entry_reads": [],
    }


def test_scope_accepts_budgeted_reasoned_planning_reads(tmp_path: Path) -> None:
    paths = _python_files(tmp_path, 2)

    normalized, scope_files = validate_scope(
        tmp_path,
        _scope(paths),
        maximum_files=5,
        maximum_planning_python_reads=2,
        maximum_implementation_entry_python_reads=2,
    )

    assert scope_files == paths
    assert [item["path"] for item in normalized["planning_reads"]] == paths


def test_scope_rejects_planning_reads_over_budget(tmp_path: Path) -> None:
    paths = _python_files(tmp_path, 3)

    with pytest.raises(ValueError, match="planning Python reads exceed maximum 2"):
        validate_scope(
            tmp_path,
            _scope(paths),
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_rejects_unscoped_planning_read(tmp_path: Path) -> None:
    path = _python_files(tmp_path, 1)[0]
    scope = _scope([])
    scope["planning_reads"] = [
        {"path": path, "reason": "Confirm the integration point."}
    ]

    with pytest.raises(ValueError, match="implementation scope path"):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_requires_explicit_planning_read_list(tmp_path: Path) -> None:
    scope = _scope([])
    del scope["planning_reads"]

    with pytest.raises(ValueError, match="planning_reads must be a list"):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_accepts_budgeted_implementation_entry_reads(tmp_path: Path) -> None:
    paths = _python_files(tmp_path, 2)
    scope = _scope(paths)
    scope["planning_reads"] = []
    scope["implementation_entry_reads"] = [
        {"path": path, "reason": "Start from the controlled change boundary."}
        for path in paths
    ]

    normalized, _ = validate_scope(
        tmp_path,
        scope,
        maximum_files=5,
        maximum_planning_python_reads=2,
        maximum_implementation_entry_python_reads=2,
    )

    assert [
        item["path"] for item in normalized["implementation_entry_reads"]
    ] == paths


def test_scope_rejects_implementation_entry_reads_over_budget(
    tmp_path: Path,
) -> None:
    paths = _python_files(tmp_path, 3)
    scope = _scope(paths)
    scope["planning_reads"] = []
    scope["implementation_entry_reads"] = [
        {"path": path, "reason": "Start from the controlled change boundary."}
        for path in paths
    ]

    with pytest.raises(
        ValueError, match="implementation entry Python reads exceed maximum 2"
    ):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_requires_explicit_implementation_entry_read_list(
    tmp_path: Path,
) -> None:
    scope = _scope([])
    del scope["implementation_entry_reads"]

    with pytest.raises(ValueError, match="implementation_entry_reads must be a list"):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_requires_one_change_target_per_write_path(tmp_path: Path) -> None:
    paths = _python_files(tmp_path, 1)
    scope = _scope(paths)
    scope["change_targets"] = []

    with pytest.raises(ValueError, match="change target missing"):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )


def test_scope_requires_verification_role_for_tests(tmp_path: Path) -> None:
    path = _python_files(tmp_path, 1)[0]
    scope = _scope([])
    scope["test_paths"] = [path]
    scope["change_targets"] = [
        {
            "path": path,
            "role": "intervention",
            "action": "modify",
            "symbols": ["<module>"],
        }
    ]

    with pytest.raises(ValueError, match="test target must use verification"):
        validate_scope(
            tmp_path,
            scope,
            maximum_files=5,
            maximum_planning_python_reads=2,
            maximum_implementation_entry_python_reads=2,
        )
