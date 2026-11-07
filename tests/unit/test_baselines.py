from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.new_experiment import create_experiment
from scripts.register_baseline import baseline_exists, register_baseline


def _payload(baseline_id: str = "BASE-TEST") -> dict:
    return {
        "schema_version": "1.0",
        "id": baseline_id,
        "title": "Source-guided image baseline",
        "source": {
            "type": "paper",
            "reference_id": "REF-TEST",
            "url": None,
            "local_path": None,
            "approved_reading_scope": ["abstract", "section 3"],
        },
        "implementation": {
            "integration_target": "src",
            "planned_paths": ["src/dl_research/models/source_baseline.py"],
        },
        "experiment": {
            "task_from_source": "derive from approved source",
            "primary_metric": "psnr",
            "dataset_assumptions": "user supplied manifest",
        },
        "notes": "",
    }


def test_register_baseline_writes_record_and_index(tmp_path: Path) -> None:
    (tmp_path / "baselines").mkdir()
    (tmp_path / "baselines/INDEX.json").write_text(
        json.dumps({"schema_version": "1.0", "baselines": []}),
        encoding="utf-8",
    )

    record = register_baseline(tmp_path, _payload())

    assert record == tmp_path / "baselines/records/BASE-TEST.json"
    assert baseline_exists(tmp_path, "BASE-TEST")
    index = json.loads((tmp_path / "baselines/INDEX.json").read_text(encoding="utf-8"))
    assert index["baselines"][0]["record"] == "baselines/records/BASE-TEST.json"


def test_register_baseline_requires_exact_reading_scope(tmp_path: Path) -> None:
    (tmp_path / "baselines").mkdir()
    (tmp_path / "baselines/INDEX.json").write_text(
        json.dumps({"schema_version": "1.0", "baselines": []}),
        encoding="utf-8",
    )
    payload = _payload()
    payload["source"]["approved_reading_scope"] = []

    with pytest.raises(ValueError, match="approved_reading_scope"):
        register_baseline(tmp_path, payload)


def test_new_experiment_rejects_unknown_baseline(tmp_path: Path) -> None:
    (tmp_path / "research").mkdir()
    (tmp_path / "research/STATE.json").write_text(
        json.dumps(
            {
                "active_experiment": None,
                "baseline_experiment": None,
                "next_action": {"mode": "select_experiment", "queue_id": "Q-001"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "experiments/active").mkdir(parents=True)
    (tmp_path / "configs/experiments").mkdir(parents=True)
    (tmp_path / "baselines").mkdir()
    (tmp_path / "baselines/INDEX.json").write_text(
        json.dumps({"schema_version": "1.0", "baselines": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown baseline ID"):
        create_experiment(
            tmp_path,
            experiment_id="EXP-TEST",
            stage="smoke",
            baseline_id="BASE-MISSING",
        )
