"""Execute one preregistered comparison sequentially, without per-run agents or retries."""

from __future__ import annotations

import json

from dl_research.experiment.comparison import require_comparison_budget, resolved_runs
from dl_research.experiment.comparison_artifacts import comparison_results
from dl_research.experiment.policy import enforce_execution_policy
from dl_research.runtime import atomic_write_json, config_sha256, relative_path


class ComparisonRunner:
    def __init__(self, parent) -> None:
        self.parent = parent
        self.raw = json.loads(parent.config.source_path.read_text(encoding="utf-8"))
        state = json.loads((parent.root / "research/STATE.json").read_text(encoding="utf-8"))
        require_comparison_budget(self.raw, state)
        enforce_execution_policy(parent.config, parent.root)
        self.digest = config_sha256(parent.config.source_path)
        self.state_path = parent.output_dir / "comparison_state.json"

    def _runs(self):
        for identity, payload in resolved_runs(self.raw):
            directory = self.parent.output_dir / "runs" / identity["run_id"]
            path = directory / "config.json"
            if path.is_file():
                if json.loads(path.read_text(encoding="utf-8")) != payload:
                    raise ValueError("comparison run config changed; do not overwrite evidence")
            else:
                atomic_write_json(path, payload)
            runner = type(self.parent).from_path(path, root=self.parent.root)
            enforce_execution_policy(runner.config, self.parent.root)
            yield identity, runner

    def sanity(self) -> dict:
        count = 0
        for _identity, runner in self._runs():
            path = runner.output_dir / "sanity.json"
            if not path.exists():
                atomic_write_json(
                    path,
                    {
                        "config_sha256": config_sha256(runner.config.source_path),
                        "result": runner.sanity(),
                    },
                )
            elif json.loads(path.read_text(encoding="utf-8")).get("config_sha256") != config_sha256(
                runner.config.source_path
            ):
                raise ValueError("comparison sanity artifact is stale")
            count += 1
        return {
            "experiment_id": self.parent.config.experiment.id,
            "comparison_runs": count,
            "config_sha256": self.digest,
            "status": "passed",
        }

    def cycle(self) -> dict:
        self.parent._prepare_output_dir()
        if self.state_path.exists():
            progress = json.loads(self.state_path.read_text(encoding="utf-8"))
            if progress.get("config_sha256") != self.digest:
                raise ValueError("comparison attempt used a different config")
            if progress.get("status") == "completed":
                comparison_results(self.parent.root, self.parent.config.source_path)
                return json.loads(
                    (self.parent.output_dir / "metrics.json").read_text(encoding="utf-8")
                )
            if progress.get("status") != "running" or any(
                run.get("status") != "completed" for run in progress.get("runs", [])
            ):
                raise ValueError("failed or interrupted comparison run; no implicit retry")
        else:
            self.sanity()
            progress = {
                "experiment_id": self.parent.config.experiment.id,
                "config_sha256": self.digest,
                "status": "running",
                "runs": [],
            }
            atomic_write_json(self.state_path, progress)
        completed = {run["run_id"]: run for run in progress["runs"]}
        for identity, runner in self._runs():
            if identity["run_id"] in completed:
                saved = completed[identity["run_id"]]
                if any(saved.get(key) != value for key, value in identity.items()):
                    raise ValueError("comparison progress identity changed")
                for name in ("metrics.json", "manifest.json"):
                    if saved.get(name) != config_sha256(runner.output_dir / name):
                        raise ValueError("completed comparison run changed before continuation")
                continue
            if (runner.output_dir / "metrics.json").exists():
                raise ValueError("untracked comparison results exist; do not overwrite evidence")
            progress["runs"].append({**identity, "status": "running"})
            atomic_write_json(self.state_path, progress)
            runner.cycle()
            progress["runs"][-1]["status"] = "completed"
            for name in ("metrics.json", "manifest.json"):
                progress["runs"][-1][name] = config_sha256(runner.output_dir / name)
            atomic_write_json(self.state_path, progress)
        summary, artifacts = comparison_results(
            self.parent.root,
            self.parent.config.source_path,
            verify_aggregate=False,
        )
        rule = self.raw["decision"]
        metrics = {
            "schema_version": "2.1",
            "experiment_id": self.parent.config.experiment.id,
            "stage": self.parent.config.experiment.stage,
            "review_mode": self.parent.config.experiment.review_mode,
            "status": "completed",
            "baseline_id": None,
            "queue_id": self.parent.config.experiment.queue_id,
            "config_sha256": self.digest,
            "primary_metric": {
                "name": rule["primary_metric"],
                "value": summary["candidate_mean"],
                "direction": rule["direction"],
                "decision_mode": rule["mode"],
                "minimum_effect": rule["minimum_effect"],
            },
            "comparison": summary,
            "training": {
                "run_count": len(artifacts),
                "max_total_batches": self.raw["comparison"]["max_total_batches"],
            },
            "test": {"aggregation": "paired_mean", "all_required_runs_completed": True},
        }
        runtime = {
            "schema_version": "2.1",
            "experiment_id": self.parent.config.experiment.id,
            "config": relative_path(self.parent.config.source_path, self.parent.root),
            "config_sha256": self.digest,
            "review_mode": self.parent.config.experiment.review_mode,
            "comparison_artifacts": artifacts,
        }
        atomic_write_json(self.parent.output_dir / "metrics.json", metrics)
        atomic_write_json(self.parent.output_dir / "manifest.json", runtime)
        progress["status"] = "completed"
        atomic_write_json(self.state_path, progress)
        return metrics
