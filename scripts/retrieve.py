from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, root_from_script, run_script


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve(root: Path, identifiers: list[str]) -> list[dict[str, Any]]:
    requested = set(identifiers)
    matches: list[dict[str, Any]] = []
    sources = [
        ("claim", root / "research/CLAIMS.jsonl"),
        ("evidence", root / "research/EVIDENCE.jsonl"),
        ("source", root / "research/SOURCES.jsonl"),
    ]
    for kind, path in sources:
        rows = [row for row in _jsonl(path) if row.get("id") in requested]
        if kind == "claim":
            latest: dict[str, dict[str, Any]] = {}
            for row in rows:
                identifier = str(row["id"])
                if int(row.get("version", 1)) >= int(latest.get(identifier, {}).get("version", 0)):
                    latest[identifier] = row
            rows = list(latest.values())
        matches.extend({"kind": kind, "record": row} for row in rows)

    indexed_sources = [
        ("experiment", root / "experiments/INDEX.json", "experiments"),
        ("reference", root / "references/INDEX.json", "records"),
    ]
    for kind, path, key in indexed_sources:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get(key, []):
            if row.get("id") in requested:
                matches.append({"kind": kind, "record": row})

    found = {entry["record"].get("id") for entry in matches}
    missing = sorted(requested - found)
    if missing:
        raise KeyError("unknown IDs: " + ", ".join(missing))
    return matches


def _execute() -> str:
    parser = QuietArgumentParser(description="Retrieve compact records by exact ID.")
    parser.add_argument("--id", nargs="+", required=True, dest="identifiers")
    args = parser.parse_args()
    records = retrieve(root_from_script(), args.identifiers)
    return json.dumps(records, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(run_script("retrieve", _execute))
