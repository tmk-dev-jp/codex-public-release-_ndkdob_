"""Model interface for research components."""

from __future__ import annotations

from abc import ABC, abstractmethod

import torch
from torch import nn


class BaseModel(nn.Module, ABC):
    """Base model with a compact parameter-count contract."""

    @abstractmethod
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """Return unnormalized task outputs."""

    def trainable_parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)
