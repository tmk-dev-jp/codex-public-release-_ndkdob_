from __future__ import annotations

import json
from pathlib import Path

import pytest

from dl_research.config import load_config
from dl_research.exceptions import ConfigError


def _trend_config(tmp_path: Path, minimum_effect: float | None) -> Path:
    payload = json.loads(Path("configs/templates/smoke.json").read_text(encoding="utf-8"))
    payload["decision"].update(
        {"mode": "trend", "minimum_effect": minimum_effect}
    )
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_config_accepts_trend_decision_without_numeric_threshold(tmp_path: Path) -> None:
    config = load_config(_trend_config(tmp_path, None))

    assert config.decision.mode == "trend"
    assert config.decision.minimum_effect is None


def test_config_rejects_numeric_threshold_in_trend_mode(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="must be null in trend mode"):
        load_config(_trend_config(tmp_path, 0.01))
