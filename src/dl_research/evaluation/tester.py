"""Silent aggregate-only test evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import torch
from torch import nn
from torch.utils.data import DataLoader

from dl_research.models.base import BaseModel


@dataclass(frozen=True)
class TestResult:
    loss: float
    accuracy: float
    samples: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Tester:
    """Evaluate a fixed model without changing parameters or printing output."""

    def __init__(
        self,
        *,
        model: BaseModel,
        loss_fn: nn.Module,
        device: torch.device,
        max_batches: int | None = None,
    ) -> None:
        self.model = model
        self.loss_fn = loss_fn
        self.device = device
        self.max_batches = max_batches

    def evaluate(self, loader: DataLoader) -> TestResult:
        self.model.to(self.device)
        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        with torch.inference_mode():
            for index, (inputs, targets) in enumerate(loader):
                if self.max_batches is not None and index >= self.max_batches:
                    break
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                outputs = self.model(inputs)
                loss = self.loss_fn(outputs, targets)
                samples = targets.shape[0]
                total_loss += float(loss) * samples
                total_correct += int((outputs.argmax(dim=1) == targets).sum())
                total_samples += samples
        if total_samples == 0:
            raise RuntimeError("test loader produced no samples")
        return TestResult(
            loss=total_loss / total_samples,
            accuracy=total_correct / total_samples,
            samples=total_samples,
        )
