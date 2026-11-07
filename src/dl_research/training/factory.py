"""Loss and optimizer factories."""

from __future__ import annotations

from torch import nn
from torch.optim import AdamW, Optimizer, SGD

from dl_research.config import OptimizerConfig
from dl_research.exceptions import ConfigError
from dl_research.models.base import BaseModel


def build_loss(name: str) -> nn.Module:
    if name == "cross_entropy":
        return nn.CrossEntropyLoss()
    raise ConfigError(f"unknown loss: {name}")


def build_optimizer(model: BaseModel, config: OptimizerConfig) -> Optimizer:
    parameters = model.parameters()
    if config.name == "adamw":
        return AdamW(
            parameters,
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
    if config.name == "sgd":
        return SGD(
            parameters,
            lr=config.learning_rate,
            momentum=config.momentum,
            weight_decay=config.weight_decay,
        )
    raise ConfigError(f"unknown optimizer: {config.name}")
