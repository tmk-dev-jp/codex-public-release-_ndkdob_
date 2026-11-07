"""Network-free synthetic classification data for templates and smoke tests."""

from __future__ import annotations

from typing import Any

import torch
from torch.utils.data import DataLoader as TorchDataLoader
from torch.utils.data import TensorDataset

from dl_research.data.base import BaseDataLoader
from dl_research.exceptions import ConfigError


class SyntheticClassificationDataLoader(BaseDataLoader):
    def __init__(
        self,
        *,
        seed: int,
        batch_size: int,
        num_workers: int,
        num_samples: int = 512,
        input_dim: int = 16,
        num_classes: int = 3,
        train_fraction: float = 0.70,
        validation_fraction: float = 0.15,
        noise: float = 0.25,
    ) -> None:
        if num_samples < 30:
            raise ConfigError("synthetic num_samples must be >= 30")
        if input_dim < 1 or num_classes < 2:
            raise ConfigError("synthetic input_dim must be >= 1 and num_classes >= 2")
        if not 0 < train_fraction < 1:
            raise ConfigError("train_fraction must be between 0 and 1")
        if not 0 < validation_fraction < 1:
            raise ConfigError("validation_fraction must be between 0 and 1")
        if train_fraction + validation_fraction >= 1:
            raise ConfigError("train and validation fractions must sum to less than 1")
        self.seed = seed
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.num_samples = num_samples
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.train_fraction = train_fraction
        self.validation_fraction = validation_fraction
        self.noise = noise
        self._train: TensorDataset | None = None
        self._validation: TensorDataset | None = None
        self._test: TensorDataset | None = None

    def setup(self) -> None:
        generator = torch.Generator().manual_seed(self.seed)
        features = torch.randn(self.num_samples, self.input_dim, generator=generator)
        weights = torch.randn(self.input_dim, self.num_classes, generator=generator)
        noise = self.noise * torch.randn(
            self.num_samples, self.num_classes, generator=generator
        )
        labels = (features @ weights + noise).argmax(dim=1)
        order = torch.randperm(self.num_samples, generator=generator)
        features = features[order]
        labels = labels[order]

        train_end = int(self.num_samples * self.train_fraction)
        validation_end = train_end + int(self.num_samples * self.validation_fraction)
        self._train = TensorDataset(features[:train_end], labels[:train_end])
        self._validation = TensorDataset(
            features[train_end:validation_end], labels[train_end:validation_end]
        )
        self._test = TensorDataset(features[validation_end:], labels[validation_end:])

    def _require_setup(self) -> tuple[TensorDataset, TensorDataset, TensorDataset]:
        if self._train is None or self._validation is None or self._test is None:
            raise RuntimeError("data loader setup() must be called first")
        return self._train, self._validation, self._test

    def train_loader(self) -> TorchDataLoader:
        train, _, _ = self._require_setup()
        generator = torch.Generator().manual_seed(self.seed + 1)
        return TorchDataLoader(
            train,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            generator=generator,
        )

    def validation_loader(self) -> TorchDataLoader:
        _, validation, _ = self._require_setup()
        return TorchDataLoader(
            validation,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
        )

    def test_loader(self) -> TorchDataLoader:
        _, _, test = self._require_setup()
        return TorchDataLoader(
            test,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
        )

    def metadata(self) -> dict[str, Any]:
        train, validation, test = self._require_setup()
        return {
            "name": "synthetic_classification",
            "input_dim": self.input_dim,
            "num_classes": self.num_classes,
            "split_sizes": {
                "train": len(train),
                "validation": len(validation),
                "test": len(test),
            },
            "seed": self.seed,
        }
