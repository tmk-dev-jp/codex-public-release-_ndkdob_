from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
)

SOURCE_TYPES = {"paper", "github", "web"}


def baseline_index_path(root: Path) -> Path:
    return root / "baselines/INDEX.json"


def baseline_record_path(root: Path, baseline_id: str) -> Path:
    return root / "baselines/records" / f"{baseline_id}.json"


def baseline_exists(root: Path, baseline_id: str) -> bool:
    index_path = baseline_index_path(root)
    if not index_path.is_file():
        return False
    index = read_json(index_path)
    return any(item.get("id") == baseline_id for item in index.get("baselines", []))


def _validate_id(baseline_id: str) -> None:
    if not re.fullmatch(r"BASE-[A-Z0-9][A-Z0-9-]*", baseline_id):
        raise ValueError("baseline ID must match BASE-[A-Z0-9-]+")


def _validate_payload(root: Path, payload: dict[str, Any]) -> None:
    _validate_id(str(payload.get("id", "")))
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    if source.get("type") not in SOURCE_TYPES:
        raise ValueError("source.type must be paper, github, or web")
    scope = source.get("approved_reading_scope")
    if (
        not isinstance(scope, list)
        or not scope
        or not all(isinstance(item, str) and item.strip() for item in scope)
    ):
        raise ValueError("source.approved_reading_scope must contain exact non-empty entries")
    local_path = source.get("local_path")
    if local_path:
        safe_relative_path(root, str(local_path), allow_missing=True)
    implementation = payload.get("implementation")
    if not isinstance(implementation, dict):
        raise ValueError("implementation must be an object")
    if implementation.get("integration_target") != "src":
        raise ValueError("implementation.integration_target must be src")
    planned = implementation.get("planned_paths", [])
    if not isinstance(planned, list):
        raise ValueError("implementation.planned_paths must be a list")
    for value in planned:
        path = safe_relative_path(root, str(value), allow_missing=True)
        if "src" not in path.relative_to(root).parts:
            raise ValueError("implementation planned paths must be under src/")


def register_baseline(root: Path, payload: dict[str, Any]) -> Path:
    _validate_payload(root, payload)
    baseline_id = str(payload["id"])
    record_path = baseline_record_path(root, baseline_id)
    if record_path.exists():
        raise FileExistsError(f"baseline already exists: {baseline_id}")
    atomic_write_json(record_path, payload)

    index_path = baseline_index_path(root)
    index = read_json(index_path)
    if any(item.get("id") == baseline_id for item in index.get("baselines", [])):
        raise ValueError(f"baseline already indexed: {baseline_id}")
    index.setdefault("baselines", []).append(
        {
            "id": baseline_id,
            "title": payload["title"],
            "record": record_path.relative_to(root).as_posix(),
            "source_type": payload["source"]["type"],
            "status": "registered",
        }
    )
    atomic_write_json(index_path, index)
    return record_path


def _execute() -> str:
    parser = QuietArgumentParser(description="Register one compact baseline record.")
    parser.add_argument("--id", required=True, dest="baseline_id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--source-type", required=True, choices=sorted(SOURCE_TYPES))
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--reference-id")
    parser.add_argument("--url")
    parser.add_argument("--local-path")
    parser.add_argument("--implementation-path", action="append", default=[])
    parser.add_argument("--metric", required=True)
    parser.add_argument("--dataset-assumption", required=True)
    parser.add_argument("--task-from-source", default="derive from approved source")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    payload = {
        "schema_version": "1.0",
        "id": args.baseline_id,
        "title": args.title,
        "source": {
            "type": args.source_type,
            "reference_id": args.reference_id,
            "url": args.url,
            "local_path": args.local_path,
            "approved_reading_scope": args.scope,
        },
        "implementation": {
            "integration_target": "src",
            "planned_paths": args.implementation_path,
        },
        "experiment": {
            "task_from_source": args.task_from_source,
            "primary_metric": args.metric,
            "dataset_assumptions": args.dataset_assumption,
        },
        "notes": args.notes,
    }
    root = root_from_script()
    return register_baseline(root, payload).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("register-baseline", _execute))
