from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, read_json, root_from_script, run_script
from scripts.workflow import require_active


def monitor_experiment(root: Path, experiment_id: str) -> str:
    _, manifest = require_active(root, experiment_id)
    result_dir = root / manifest["result_dir"]
    phase = str(manifest.get("phase"))
    if (result_dir / "error.json").is_file():
        error = read_json(result_dir / "error.json")
        return f"{experiment_id} status=failed phase={phase} error={error.get('error_type', 'unknown')}"
    if (result_dir / "metrics.json").is_file():
        metrics = read_json(result_dir / "metrics.json")
        primary = metrics.get("primary_metric", {})
        name = primary.get("name", "metric")
        value = primary.get("value", "unknown")
        return f"{experiment_id} status=completed phase={phase} {name}={value}"
    if (result_dir / "comparison_state.json").is_file():
        progress = read_json(result_dir / "comparison_state.json")
        done = sum(run.get("status") == "completed" for run in progress.get("runs", []))
        return f"{experiment_id} status={progress.get('status')} phase={phase} completed_runs={done}"
    if result_dir.is_dir() and (result_dir / "sanity.json").is_file():
        return f"{experiment_id} status=sanity-passed phase={phase}"
    if result_dir.is_dir():
        return f"{experiment_id} status=running-or-prepared phase={phase}"
    return f"{experiment_id} status=not-started phase={phase}"


def _execute() -> str:
    parser = QuietArgumentParser(description="Report compact experiment artifact status.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    return monitor_experiment(root_from_script(), args.experiment_id)


if __name__ == "__main__":
    raise SystemExit(run_script("monitor-experiment", _execute))
