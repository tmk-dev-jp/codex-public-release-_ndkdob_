"""Explicitly close a failed comparison without deleting or accepting its evidence."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.build_digest import build_digest
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    one_line,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_file,
)
from scripts.workflow import ALLOWED_TRANSITIONS, comparison_results_recorded, require_active


def _snapshot(root: Path, directory: Path, manifest: dict) -> dict:
    result = safe_relative_path(root, manifest["result_dir"])
    paths = {
        "record": directory / "EXPERIMENT.md",
        "scope": directory / "SCOPE.json",
        "config": safe_relative_path(root, manifest["config"], allow_missing=True),
        **{
            name: result / name
            for name in ("comparison_state.json", "metrics.json", "manifest.json", "error.json")
        },
    }
    return {name: sha256_file(path) if path.is_file() else None for name, path in paths.items()}


def abort_comparison(
    root: Path, experiment_id: str, *, reason: str, confirm_abort: bool = False
) -> Path:
    if not confirm_abort:
        raise ValueError("explicit human abort instruction and --confirm-abort are required")
    if not re.fullmatch(r"EXP-[A-Z0-9][A-Z0-9-]*", experiment_id):
        raise ValueError("invalid experiment ID")
    reason = one_line(reason)
    if not reason or len(reason) > 400 or reason.lower() in {"pending", "none", "unknown"}:
        raise ValueError("a concrete abort reason of 1 to 400 characters is required")
    active = root / "experiments/active" / experiment_id
    archived = safe_relative_path(root, f"experiments/aborted/{experiment_id}", allow_missing=True)
    if active.exists() and archived.exists():
        raise FileExistsError("both active and archived experiment directories exist")
    directory = archived if archived.exists() else active
    closure_path = directory / "ABORTION.json"
    state = read_json(root / "research/STATE.json")
    index = read_json(root / "experiments/INDEX.json")
    matches = [item for item in index.get("experiments", []) if item.get("id") == experiment_id]
    if len(matches) != 1:
        raise ValueError("experiment must have exactly one index entry")
    item = matches[0]
    if state.get("active_experiment") != experiment_id and not (
        state.get("active_experiment") is None
        and state.get("phase") is None
        and state.get("latest_aborted_experiment") == experiment_id
        and item.get("status") == "aborted"
        and archived.exists()
    ):
        raise ValueError("abort target is not the active or just-aborted experiment")
    if state.get("active_experiment") == experiment_id and state.get("phase") != "FAILED":
        raise ValueError("only a FAILED comparison can be aborted")
    if "ABORTED" not in ALLOWED_TRANSITIONS["FAILED"]:
        raise ValueError("FAILED -> ABORTED transition is not allowed")
    # Persist the closure before moving records so an explicit repeat can finish interrupted writes.
    if closure_path.exists():
        closure = read_json(closure_path)
        if closure.get("experiment_id") != experiment_id or closure.get("reason") != reason:
            raise ValueError("abort ID or reason differs from the prepared closure")
        original = closure["original_manifest"]
        if closure.get("preserved_inputs") != _snapshot(root, directory, original):
            raise ValueError("preserved abort inputs changed; do not overwrite the closure")
    else:
        if archived.exists():
            raise FileExistsError("archive exists without a prepared closure")
        _, original = require_active(root, experiment_id, {"FAILED"})
        if not comparison_results_recorded(root, original):
            raise ValueError("recorded comparison execution is required")
        closure = {
            "schema_version": "1.0",
            "experiment_id": experiment_id,
            "reason": reason,
            "scientific_outcome": "not_evaluated",
            "original_manifest": original,
            "original_index_entry": dict(item),
            "preserved_inputs": _snapshot(root, active, original),
        }
    relative = f"experiments/aborted/{experiment_id}"
    terminal = {
        **original,
        "status": "aborted",
        "phase": "ABORTED",
        "record": f"{relative}/EXPERIMENT.md",
        "scope": f"{relative}/SCOPE.json",
        "abortion": f"{relative}/ABORTION.json",
    }
    terminal_item = {
        **closure["original_index_entry"],
        "status": "aborted",
        "phase": "ABORTED",
        "record": terminal["record"],
        "abortion": terminal["abortion"],
        "abort_reason": reason,
    }
    if read_json(directory / "MANIFEST.json") not in (original, terminal):
        raise ValueError("experiment manifest changed during abort")
    if item not in (closure["original_index_entry"], terminal_item):
        raise ValueError("experiment index entry changed during abort")
    if not closure_path.exists():
        atomic_write_json(closure_path, closure)
    if directory == active:
        archived.parent.mkdir(parents=True, exist_ok=True)
        active.rename(archived)
    atomic_write_json(archived / "MANIFEST.json", terminal)
    item.update(terminal_item)
    atomic_write_json(root / "experiments/INDEX.json", index)
    if state.get("active_experiment") == experiment_id:
        state.update(
            project_status="ready",
            active_experiment=None,
            phase=None,
            stage=None,
            review_required=False,
            latest_aborted_experiment=experiment_id,
            next_action={
                "mode": "select_experiment",
                "queue_id": original.get("queue_id"),
                "objective": (
                    f"Review the abort reason for {experiment_id} in experiments/DIGEST.md; "
                    "select a new ID only with a concrete remedy and fresh plan approval."
                ),
            },
        )
        for key in ("plan_review_experiment_id", "full_training_experiment_id"):
            if state.get("approvals", {}).get(key) == experiment_id:
                state["approvals"][key] = None
        if state.get("unattended_loop", {}).get("target_experiment") == experiment_id:
            state["unattended_loop"] = {
                "status": "idle",
                "target_experiment": None,
                "last_mode": None,
            }
        atomic_write_json(root / "research/STATE.json", state)
    build_digest(root)
    build_context(root)
    return archived


def _execute() -> str:
    parser = QuietArgumentParser(description="Explicitly abort a failed, recorded comparison.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--confirm-abort", action="store_true")
    args = parser.parse_args()
    root = root_from_script()
    return (
        abort_comparison(
            root, args.experiment_id, reason=args.reason, confirm_abort=args.confirm_abort
        )
        .relative_to(root)
        .as_posix()
    )


if __name__ == "__main__":
    raise SystemExit(run_script("abort-comparison", _execute))
