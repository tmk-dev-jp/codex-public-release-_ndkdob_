"""Explicit data-loader factory."""

from __future__ import annotations

from dl_research.config import DataConfig
from dl_research.data.base import BaseDataLoader
from dl_research.data.synthetic import SyntheticClassificationDataLoader
from dl_research.exceptions import ConfigError


def build_data_loader(config: DataConfig, *, seed: int) -> BaseDataLoader:
    if config.name == "synthetic_classification":
        return SyntheticClassificationDataLoader(
            seed=seed,
            batch_size=config.batch_size,
            num_workers=config.num_workers,
            **config.parameters,
        )
    raise ConfigError(f"unknown data loader: {config.name}")
