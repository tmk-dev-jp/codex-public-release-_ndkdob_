from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
)


def complete_direction_update(root: Path) -> str:
    state = read_json(root / "research/STATE.json")
    if state.get("active_experiment") is not None:
        raise ValueError("direction completion requires no active experiment")
    if state.get("next_action", {}).get("mode") != "update_direction":
        raise ValueError("next action is not update_direction")
    queue_id = state.get("next_action", {}).get("queue_id")
    state["next_action"] = {
        "mode": "select_experiment",
        "queue_id": queue_id,
        "objective": "Select or create exactly one next experiment from the updated queue.",
    }
    atomic_write_json(root / "research/STATE.json", state)
    build_context(root)
    return "select_experiment"


def _execute() -> str:
    parser = QuietArgumentParser(description="Advance after research direction is updated.")
    parser.parse_args()
    return complete_direction_update(root_from_script())


if __name__ == "__main__":
    raise SystemExit(run_script("complete-direction-update", _execute))
