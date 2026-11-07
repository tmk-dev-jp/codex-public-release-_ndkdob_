"""Data-loader interface used by trainers and testers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from torch.utils.data import DataLoader as TorchDataLoader


class BaseDataLoader(ABC):
    """Build deterministic train, validation, and test loaders."""

    @abstractmethod
    def setup(self) -> None:
        """Create datasets and deterministic splits without network access."""

    @abstractmethod
    def train_loader(self) -> TorchDataLoader:
        """Return the shuffled training loader."""

    @abstractmethod
    def validation_loader(self) -> TorchDataLoader:
        """Return the non-shuffled validation loader."""

    @abstractmethod
    def test_loader(self) -> TorchDataLoader:
        """Return the non-shuffled test loader."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return compact dataset facts without sample content."""
