from __future__ import annotations

import json
from pathlib import Path

from dl_research.experiment.runner import ExperimentRunner


def test_complete_smoke_cycle_writes_only_aggregate_artifacts(tmp_path: Path, capsys) -> None:
    (tmp_path / "research").mkdir()
    state = json.loads(Path("research/STATE.json").read_text(encoding="utf-8"))
    (tmp_path / "research/STATE.json").write_text(json.dumps(state), encoding="utf-8")
    (tmp_path / "configs").mkdir()
    config = json.loads(Path("configs/templates/smoke.json").read_text(encoding="utf-8"))
    config["experiment"]["id"] = "EXP-TEST"
    config["experiment"]["output_dir"] = "artifacts/results/EXP-TEST"
    config_path = tmp_path / "configs/EXP-TEST.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    runner = ExperimentRunner.from_path(config_path, root=tmp_path)
    sanity = runner.sanity()
    result = runner.cycle()
    output = tmp_path / "artifacts/results/EXP-TEST"

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert sanity["gradient_tensors"] > 0
    assert result["status"] == "completed"
    assert (output / "metrics.json").is_file()
    assert (output / "manifest.json").is_file()
    assert not (output / "history.json").exists()
    assert not (output / "train_metrics.json").exists()
    assert not (output / "test_metrics.json").exists()
    assert (output / "AGENTS.md").is_file()
    assert not any(output.glob("*.log"))
