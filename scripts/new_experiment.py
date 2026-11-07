from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_context import build_context
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
)
from scripts.register_baseline import baseline_exists
from scripts.research_memory import NOVELTY_CONTRACT_VERSION


def _active_directories(path: Path) -> list[Path]:
    return [entry for entry in path.iterdir() if entry.is_dir() and not entry.name.startswith(".")]


def create_experiment(
    root: Path,
    *,
    experiment_id: str,
    stage: str,
    queue_id: str | None = None,
    baseline_id: str | None = None,
) -> Path:
    if not re.fullmatch(r"EXP-[A-Z0-9][A-Z0-9-]*", experiment_id):
        raise ValueError("experiment ID must match EXP-[A-Z0-9-]+")
    if stage not in {"smoke", "pilot", "full"}:
        raise ValueError("stage must be smoke, pilot, or full")

    state_path = root / "research/STATE.json"
    state = read_json(state_path)
    active_root = root / "experiments/active"
    active = _active_directories(active_root)
    if active or state.get("active_experiment"):
        raise RuntimeError("an active experiment already exists")
    if state.get("next_action", {}).get("mode") != "select_experiment":
        raise ValueError("next action is not select_experiment")

    queue_id = queue_id or state.get("next_action", {}).get("queue_id") or "Q-001"
    baseline_id = baseline_id or state.get("baseline_experiment")
    if baseline_id and not baseline_exists(root, baseline_id):
        raise ValueError(f"unknown baseline ID: {baseline_id}")
    index_path = root / "experiments/INDEX.json"
    index = read_json(index_path)
    if any(item.get("id") == experiment_id for item in index.get("experiments", [])):
        raise ValueError(f"experiment already indexed: {experiment_id}")
    experiment_dir = active_root / experiment_id
    config_path = root / "configs/experiments" / f"{experiment_id}.json"
    if experiment_dir.exists() or config_path.exists():
        raise FileExistsError(f"experiment already exists: {experiment_id}")

    record_template = (root / "experiments/templates/EXPERIMENT.md").read_text(encoding="utf-8")
    record = record_template.replace("{{EXPERIMENT_ID}}", experiment_id)
    config = read_json(root / "configs/templates" / f"{stage}.json")
    config["experiment"].update(
        {
            "id": experiment_id,
            "stage": stage,
            "output_dir": f"artifacts/results/{experiment_id}",
            "baseline_id": baseline_id,
            "queue_id": queue_id,
        }
    )
    scope = read_json(root / "experiments/templates/SCOPE.json")
    manifest = read_json(root / "experiments/templates/MANIFEST.json")
    manifest.update(
        {
            "id": experiment_id,
            "novelty_contract_version": NOVELTY_CONTRACT_VERSION,
            "stage": stage,
            "queue_id": queue_id,
            "baseline_id": baseline_id,
            "record": f"experiments/active/{experiment_id}/EXPERIMENT.md",
            "scope": f"experiments/active/{experiment_id}/SCOPE.json",
            "config": f"configs/experiments/{experiment_id}.json",
            "result_dir": f"artifacts/results/{experiment_id}",
        }
    )

    experiment_dir.mkdir(parents=True)
    experiment_agents = (
        root / "experiments/templates/EXPERIMENT_AGENTS.md"
    ).read_text(encoding="utf-8")
    atomic_write_text(experiment_dir / "AGENTS.md", experiment_agents)
    atomic_write_text(experiment_dir / "EXPERIMENT.md", record)
    atomic_write_json(experiment_dir / "SCOPE.json", scope)
    atomic_write_json(experiment_dir / "MANIFEST.json", manifest)
    atomic_write_json(config_path, config)

    index.setdefault("experiments", []).append(
        {
            "id": experiment_id,
            "stage": stage,
            "status": "active",
            "phase": "DRAFT",
            "record": manifest["record"],
            "config": manifest["config"],
            "metrics": f"artifacts/results/{experiment_id}/metrics.json",
        }
    )
    atomic_write_json(index_path, index)

    state.update(
        {
            "project_status": "active",
            "active_experiment": experiment_id,
            "phase": "DRAFT",
            "stage": stage,
            "review_required": False,
            "next_action": {
                "mode": "plan_experiment",
                "queue_id": queue_id,
                "objective": (
                    "Fill the active hypothesis, method, config, and exact file scope, "
                    "then lock the plan."
                ),
            },
        }
    )
    state.setdefault("approvals", {})["plan_review_experiment_id"] = None
    atomic_write_json(state_path, state)
    build_context(root)
    return experiment_dir


def _execute() -> str:
    parser = QuietArgumentParser(description="Create one active experiment draft.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--stage", choices=["smoke", "pilot", "full"], required=True)
    parser.add_argument("--queue-id")
    parser.add_argument("--baseline-id")
    args = parser.parse_args()
    root = root_from_script()
    path = create_experiment(
        root,
        experiment_id=args.experiment_id,
        stage=args.stage,
        queue_id=args.queue_id,
        baseline_id=args.baseline_id,
    )
    return path.relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("new-experiment", _execute))
