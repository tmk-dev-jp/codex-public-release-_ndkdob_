from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_decision_facts import (
    DecisionFactsRequiredError,
    build_decision_facts,
    require_current_decision_facts,
)
from scripts.common import sha256_file

EXPERIMENT_ID = "EXP-FACTS"
BASELINE_ID = "EXP-BASE"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _metric(
    value: float,
    *,
    direction: str = "maximize",
    mode: str = "threshold",
    minimum_effect: float | None = 0.01,
    name: str = "test_accuracy",
) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "baseline_id": None,
        "status": "completed",
        "primary_metric": {
            "name": name,
            "value": value,
            "direction": direction,
            "decision_mode": mode,
            "minimum_effect": minimum_effect,
        },
        "training": {},
        "test": {},
    }


def _root(
    root: Path,
    *,
    current: float = 0.72,
    baseline: float | None = 0.70,
    direction: str = "maximize",
    mode: str = "threshold",
    minimum_effect: float | None = 0.01,
) -> Path:
    active = root / "experiments/active" / EXPERIMENT_ID
    active.mkdir(parents=True)
    baseline_id = BASELINE_ID if baseline is not None else None
    _write_json(
        root / "research/STATE.json",
        {
            "active_experiment": EXPERIMENT_ID,
            "phase": "TRAINED",
            "next_action": {"mode": "trained"},
        },
    )
    config_path = root / f"configs/experiments/{EXPERIMENT_ID}.json"
    _write_json(
        config_path,
        {
            "experiment": {"id": EXPERIMENT_ID, "baseline_id": baseline_id},
            "decision": {
                "primary_metric": "test_accuracy",
                "direction": direction,
                "mode": mode,
                "minimum_effect": minimum_effect,
            },
        },
    )
    config_hash = sha256_file(config_path)
    _write_json(
        active / "MANIFEST.json",
        {
            "id": EXPERIMENT_ID,
            "phase": "TRAINED",
            "baseline_id": baseline_id,
            "config": f"configs/experiments/{EXPERIMENT_ID}.json",
            "locked_config_sha256": config_hash,
            "result_dir": f"artifacts/results/{EXPERIMENT_ID}",
        },
    )
    current_metric = _metric(
        current,
        direction=direction,
        mode=mode,
        minimum_effect=minimum_effect,
    )
    current_metric["baseline_id"] = baseline_id
    current_metric["config_sha256"] = config_hash
    _write_json(
        root / f"artifacts/results/{EXPERIMENT_ID}/metrics.json",
        current_metric,
    )
    experiments = []
    if baseline is not None:
        baseline_path = f"artifacts/results/{BASELINE_ID}/metrics.json"
        baseline_metric = _metric(
            baseline,
            direction=direction,
            mode=mode,
            minimum_effect=minimum_effect,
        )
        baseline_metric["experiment_id"] = BASELINE_ID
        _write_json(root / baseline_path, baseline_metric)
        experiments.append({"id": BASELINE_ID, "metrics": baseline_path})
    _write_json(root / "experiments/INDEX.json", {"experiments": experiments})
    return active


def test_build_decision_facts_computes_maximize_threshold(tmp_path: Path) -> None:
    active = _root(tmp_path)

    path = build_decision_facts(tmp_path, EXPERIMENT_ID)
    facts = json.loads(path.read_text(encoding="utf-8"))

    assert abs(facts["comparison"]["oriented_effect"] - 0.02) < 1e-12
    assert facts["decision_rule"]["status"] == "met"
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    assert require_current_decision_facts(tmp_path, active, manifest) == facts


def test_build_decision_facts_handles_minimize_and_not_met(tmp_path: Path) -> None:
    _root(
        tmp_path,
        current=0.695,
        baseline=0.70,
        direction="minimize",
        minimum_effect=0.01,
    )

    facts = json.loads(
        build_decision_facts(tmp_path, EXPERIMENT_ID).read_text(encoding="utf-8")
    )

    assert abs(facts["comparison"]["oriented_effect"] - 0.005) < 1e-12
    assert facts["decision_rule"]["status"] == "not_met"


def test_build_decision_facts_marks_trend_for_interpretation(tmp_path: Path) -> None:
    _root(
        tmp_path,
        mode="trend",
        minimum_effect=None,
    )

    facts = json.loads(
        build_decision_facts(tmp_path, EXPERIMENT_ID).read_text(encoding="utf-8")
    )

    assert facts["decision_rule"]["status"] == "trend_requires_interpretation"


def test_build_decision_facts_rejects_metric_mismatch(tmp_path: Path) -> None:
    _root(tmp_path)
    metrics_path = tmp_path / f"artifacts/results/{EXPERIMENT_ID}/metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["primary_metric"]["name"] = "shortcut_accuracy"
    _write_json(metrics_path, metrics)

    with pytest.raises(ValueError, match="does not match locked config"):
        build_decision_facts(tmp_path, EXPERIMENT_ID)


def test_build_decision_facts_rejects_changed_locked_config(tmp_path: Path) -> None:
    _root(tmp_path)
    config_path = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["decision"]["minimum_effect"] = 0.02
    _write_json(config_path, config)

    with pytest.raises(ValueError, match="config changed after plan locking"):
        build_decision_facts(tmp_path, EXPERIMENT_ID)


def test_build_decision_facts_rejects_changed_baseline(tmp_path: Path) -> None:
    active = _root(tmp_path)
    manifest_path = active / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["baseline_id"] = None
    _write_json(manifest_path, manifest)

    with pytest.raises(ValueError, match="manifest baseline"):
        build_decision_facts(tmp_path, EXPERIMENT_ID)


def test_build_decision_facts_tolerates_float_boundary_noise(tmp_path: Path) -> None:
    _root(
        tmp_path,
        current=0.3,
        baseline=0.2,
        minimum_effect=0.1,
    )

    facts = json.loads(
        build_decision_facts(tmp_path, EXPERIMENT_ID).read_text(encoding="utf-8")
    )

    assert facts["decision_rule"]["status"] == "met"


def test_decision_facts_invalidate_when_metrics_change(tmp_path: Path) -> None:
    active = _root(tmp_path)
    build_decision_facts(tmp_path, EXPERIMENT_ID)
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    metrics_path = tmp_path / f"artifacts/results/{EXPERIMENT_ID}/metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["primary_metric"]["value"] = 0.8
    _write_json(metrics_path, metrics)

    with pytest.raises(DecisionFactsRequiredError, match="inputs changed"):
        require_current_decision_facts(tmp_path, active, manifest)
