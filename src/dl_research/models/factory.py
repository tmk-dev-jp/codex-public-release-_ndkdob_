"""Explicit model factory."""

from __future__ import annotations

from dl_research.config import ModelConfig
from dl_research.exceptions import ConfigError
from dl_research.models.base import BaseModel
from dl_research.models.mlp import MLPClassifier


def build_model(config: ModelConfig) -> BaseModel:
    if config.name == "mlp_classifier":
        return MLPClassifier(**config.parameters)
    raise ConfigError(f"unknown model: {config.name}")
