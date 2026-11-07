from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.common import QuietArgumentParser, atomic_write_json, root_from_script, run_script
from scripts.workflow import require_active, state_path


def approve_full(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"PLANNED", "IMPLEMENTED"})
    if manifest.get("stage") != "full":
        raise ValueError("only a full-stage experiment needs this approval")
    state.setdefault("approvals", {})["full_training_experiment_id"] = experiment_id
    atomic_write_json(state_path(root), state)
    build_context(root)
    return state_path(root)


def _execute() -> str:
    parser = QuietArgumentParser(description="Approve one active full experiment.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return approve_full(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("approve-full", _execute))
