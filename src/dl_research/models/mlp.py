"""Small multilayer perceptron classifier."""

from __future__ import annotations

import torch
from torch import nn

from dl_research.models.base import BaseModel


class MLPClassifier(BaseModel):
    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dims: list[int],
        num_classes: int,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if input_dim < 1 or num_classes < 2:
            raise ValueError("input_dim must be >= 1 and num_classes must be >= 2")
        if any(width < 1 for width in hidden_dims):
            raise ValueError("hidden dimensions must be positive")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in [0, 1)")

        layers: list[nn.Module] = []
        previous = input_dim
        for width in hidden_dims:
            layers.extend([nn.Linear(previous, width), nn.ReLU()])
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            previous = width
        layers.append(nn.Linear(previous, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.network(inputs)
