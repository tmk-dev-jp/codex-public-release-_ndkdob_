from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.implementation_delta import (
    ImplementationDeltaRequiredError,
    complete_implementation_delta,
    lock_implementation_delta,
    require_current_implementation_delta,
)

EXPERIMENT_ID = "EXP-DELTA"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _record() -> str:
    return f"""# {EXPERIMENT_ID}

## Hypothesis

- Claim: the candidate changes the measured behavior

## Method

- Implementation: change one declared function
- Baseline behavior: transform returns its input
- Candidate behavior: transform adds one
- Intervention point: src/model.py transform
- Unchanged invariants: helper behavior and all evaluation controls

## Conclusion

- Decision: pending

## Issues and Next Direction

- Main issue: pending
"""


def _scope(path: str, *, action: str = "modify", symbol: str = "transform") -> dict:
    return {
        "schema_version": "1.3",
        "read_paths": [],
        "write_paths": [path],
        "test_paths": [],
        "change_targets": [
            {
                "path": path,
                "role": "intervention",
                "action": action,
                "symbols": [symbol],
            }
        ],
        "planning_reads": [],
        "implementation_entry_reads": [],
    }


def _git_repository(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "src/model.py", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Delta Test",
            "-c",
            "user.email=delta@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
    )


def _root(root: Path, scope: dict) -> tuple[Path, dict]:
    active = root / "experiments/active" / EXPERIMENT_ID
    active.mkdir(parents=True)
    (active / "EXPERIMENT.md").write_text(_record(), encoding="utf-8")
    _write_json(active / "SCOPE.json", scope)
    _write_json(root / "configs/experiments/EXP-DELTA.json", {})
    manifest = {
        "id": EXPERIMENT_ID,
        "config": "configs/experiments/EXP-DELTA.json",
    }
    _, metadata = lock_implementation_delta(
        root,
        EXPERIMENT_ID,
        _record(),
        scope,
        manifest["config"],
    )
    manifest["implementation_delta"] = metadata
    return active, manifest


def test_delta_records_declared_and_observed_symbol_change(tmp_path: Path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def transform(value):\n    return value\n\n\ndef helper(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git_repository(tmp_path)
    active, manifest = _root(tmp_path, _scope("src/model.py"))

    source.write_text(
        "def transform(value):\n    return value + 1\n\n\ndef helper(value):\n    return value\n",
        encoding="utf-8",
    )
    delta_path, metadata = complete_implementation_delta(
        tmp_path, active, manifest
    )
    manifest["implementation_delta"] = metadata

    payload = json.loads(delta_path.read_text(encoding="utf-8"))
    target = payload["targets"][0]
    assert payload["status"] == "implemented"
    assert target["before"]["sha256"] != target["after"]["sha256"]
    assert target["observed_change"] == "modify"
    assert "transform" in target["observed_changed_symbols"]
    assert "helper" not in target["observed_changed_symbols"]
    require_current_implementation_delta(tmp_path, active, manifest)


def test_delta_rejects_undeclared_workspace_change(tmp_path: Path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("def transform(value):\n    return value\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("baseline\n", encoding="utf-8")
    _git_repository(tmp_path)
    active, manifest = _root(tmp_path, _scope("src/model.py"))

    source.write_text("def transform(value):\n    return value + 1\n", encoding="utf-8")
    readme.write_text("undeclared\n", encoding="utf-8")

    with pytest.raises(
        ImplementationDeltaRequiredError,
        match="undeclared workspace change",
    ):
        complete_implementation_delta(tmp_path, active, manifest)


def test_delta_records_scoped_repair(tmp_path: Path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("def transform(value):\n    return value\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git_repository(tmp_path)
    active, manifest = _root(tmp_path, _scope("src/model.py"))

    source.write_text("def transform(value):\n    return value + 1\n", encoding="utf-8")
    _, metadata = complete_implementation_delta(tmp_path, active, manifest)
    manifest["implementation_delta"] = metadata
    source.write_text("def transform(value):\n    return value + 2\n", encoding="utf-8")

    delta_path, metadata = complete_implementation_delta(
        tmp_path,
        active,
        manifest,
        repair=True,
    )
    manifest["implementation_delta"] = metadata
    payload = json.loads(delta_path.read_text(encoding="utf-8"))

    assert payload["repairs"][0]["sequence"] == 1
    assert payload["repairs"][0]["targets"][0]["observed_change"] == "modify"
    require_current_implementation_delta(tmp_path, active, manifest)


def test_delta_rejects_change_to_wrong_symbol(tmp_path: Path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def transform(value):\n    return value\n\n\ndef helper(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git_repository(tmp_path)
    active, manifest = _root(tmp_path, _scope("src/model.py"))

    source.write_text(
        "def transform(value):\n    return value\n\n\ndef helper(value):\n    return value + 1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ImplementationDeltaRequiredError,
        match="declared symbol did not change",
    ):
        complete_implementation_delta(tmp_path, active, manifest)


def test_delta_classifies_created_file(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Delta Test",
            "-c",
            "user.email=delta@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
    )
    scope = _scope("src/candidate.py", action="create", symbol="candidate")
    active, manifest = _root(tmp_path, scope)

    candidate = tmp_path / "src/candidate.py"
    candidate.write_text("def candidate(value):\n    return value + 1\n", encoding="utf-8")
    delta_path, _ = complete_implementation_delta(tmp_path, active, manifest)

    target = json.loads(delta_path.read_text(encoding="utf-8"))["targets"][0]
    assert target["action"] == "create"
    assert target["observed_change"] == "create"
    assert target["before"]["exists"] is False
    assert target["after"]["exists"] is True


def test_delta_rejects_extra_undeclared_symbol_change(tmp_path: Path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def transform(value):\n    return value\n\n\ndef helper(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git_repository(tmp_path)
    active, manifest = _root(tmp_path, _scope("src/model.py"))

    source.write_text(
        "def transform(value):\n    return value + 1\n\n\ndef helper(value):\n    return value + 1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ImplementationDeltaRequiredError,
        match="undeclared symbol changed",
    ):
        complete_implementation_delta(tmp_path, active, manifest)
