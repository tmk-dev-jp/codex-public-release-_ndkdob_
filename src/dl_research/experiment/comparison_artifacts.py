"""Verify every declared comparison result without loading ML libraries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dl_research.experiment.comparison import resolved_runs, summarize_comparison


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison_results(
    root: Path, config_path: Path, *, verify_aggregate: bool = True
) -> tuple[dict, list]:
    raw = _read(config_path)
    output = (root / raw["experiment"]["output_dir"]).resolve()
    output.relative_to(root.resolve())
    rows, artifacts = [], []
    datasets: dict[str, dict] = {}
    metric_rule = raw["decision"]
    for identity, expected_config in resolved_runs(raw):
        directory = output / "runs" / identity["run_id"]
        paths = {
            name: directory / name for name in ("config.json", "metrics.json", "manifest.json")
        }
        if _read(paths["config.json"]) != expected_config:
            raise ValueError("comparison child config differs from the locked design")
        digest = _hash(paths["config.json"])
        metrics, manifest = _read(paths["metrics.json"]), _read(paths["manifest.json"])
        for payload in (metrics, manifest):
            if payload.get("experiment_id") != raw["experiment"]["id"]:
                raise ValueError("comparison child experiment ID differs")
            if payload.get("config_sha256") != digest:
                raise ValueError("comparison child artifact config hash differs")
            if payload.get("review_mode") != raw["experiment"]["review_mode"]:
                raise ValueError("comparison child review mode differs")
        if (
            metrics.get("status") != "completed"
            or metrics.get("stage") != raw["experiment"]["stage"]
        ):
            raise ValueError("comparison child is incomplete or has a different stage")
        metric = metrics.get("primary_metric", {})
        for key, value in (
            ("name", metric_rule["primary_metric"]),
            ("direction", metric_rule["direction"]),
            ("decision_mode", metric_rule["mode"]),
            ("minimum_effect", metric_rule["minimum_effect"]),
        ):
            if metric.get(key) != value:
                raise ValueError("comparison child metric rule differs")
        dataset = manifest.get("dataset")
        if not isinstance(dataset, dict) or not dataset:
            raise ValueError("comparison child dataset metadata is missing")
        condition = identity["condition"]
        if condition in datasets and dataset != datasets[condition]:
            raise ValueError("comparison arms or training seeds used different dataset metadata")
        datasets[condition] = dataset
        rows.append({**identity, "value": metric.get("value")})
        artifacts.append(
            {
                "run_id": identity["run_id"],
                **{
                    name.removesuffix(".json") + "_sha256": _hash(path)
                    for name, path in paths.items()
                },
            }
        )
    summary = summarize_comparison(raw, rows)
    if verify_aggregate:
        aggregate, runtime = _read(output / "metrics.json"), _read(output / "manifest.json")
        progress = _read(output / "comparison_state.json")
        if progress.get("status") != "completed" or progress.get("config_sha256") != _hash(
            config_path
        ):
            raise ValueError("comparison execution has not completed under the locked config")
        if (
            aggregate.get("comparison") != summary
            or runtime.get("comparison_artifacts") != artifacts
        ):
            raise ValueError("comparison summary or child artifacts changed")
        if aggregate.get("primary_metric", {}).get("value") != summary["candidate_mean"]:
            raise ValueError("comparison primary value does not match all required runs")
        if aggregate.get("status") != "completed" or aggregate.get("config_sha256") != _hash(
            config_path
        ):
            raise ValueError("comparison aggregate is incomplete or stale")
    return summary, artifacts


def comparison_input_hash(root: Path, config_path: Path) -> str | None:
    if "comparison" not in _read(config_path):
        return None
    summary, artifacts = comparison_results(root, config_path)
    material = json.dumps([summary, artifacts], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
