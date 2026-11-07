from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from dl_research.config import load_config
from dl_research.data.factory import build_data_loader
from dl_research.exceptions import ConfigError
from dl_research.evaluation.tester import Tester as EvaluationTester
from dl_research.models.factory import build_model
from dl_research.runtime import resolve_device
from dl_research.training.factory import build_loss, build_optimizer
from dl_research.training.trainer import Trainer


def test_component_contracts_are_silent(tmp_path: Path, capsys) -> None:
    config = load_config(Path("configs/templates/smoke.json"))
    data = build_data_loader(config.data, seed=config.experiment.seed)
    data.setup()
    model = build_model(config.model)
    loss = build_loss(config.train.loss)
    optimizer = build_optimizer(model, config.train.optimizer)
    device = resolve_device("cpu")
    checkpoint = tmp_path / "best.pt"

    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        loss_fn=loss,
        device=device,
        config=config.train,
        checkpoint_path=checkpoint,
    )
    train_result = trainer.fit(data.train_loader(), data.validation_loader())
    payload = torch.load(checkpoint, map_location=device, weights_only=True)
    model.load_state_dict(payload["model_state"])
    test_result = EvaluationTester(
        model=model,
        loss_fn=loss,
        device=device,
        max_batches=2,
    ).evaluate(data.test_loader())

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert train_result.epochs_completed == 1
    assert torch.isfinite(torch.tensor(train_result.best_validation_loss))
    assert config.train.checkpoint_metric == "loss"
    assert config.train.checkpoint_mode == "min"
    assert 0.0 <= test_result.accuracy <= 1.0
    assert test_result.samples > 0


def _write_modified_smoke_config(
    tmp_path: Path,
    train_updates: dict,
) -> Path:
    payload = json.loads(Path("configs/templates/smoke.json").read_text(encoding="utf-8"))
    payload["train"].update(train_updates)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_config_requires_validation_loss_checkpoint_metric(tmp_path: Path) -> None:
    path = _write_modified_smoke_config(tmp_path, {"checkpoint_metric": "accuracy"})

    with pytest.raises(ConfigError, match="checkpoint_metric must be loss"):
        load_config(path)


def test_config_requires_validation_loss_checkpoint_mode(tmp_path: Path) -> None:
    path = _write_modified_smoke_config(tmp_path, {"checkpoint_mode": "max"})

    with pytest.raises(ConfigError, match="checkpoint_mode must be min"):
        load_config(path)


def test_config_requires_early_stopping_patience(tmp_path: Path) -> None:
    path = _write_modified_smoke_config(tmp_path, {"early_stopping_patience": None})

    with pytest.raises(ConfigError, match="early_stopping_patience is required"):
        load_config(path)
