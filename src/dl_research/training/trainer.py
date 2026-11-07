"""Silent aggregate-only training loop."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import Optimizer
from torch.utils.data import DataLoader

from dl_research.config import TrainConfig
from dl_research.models.base import BaseModel


@dataclass(frozen=True)
class TrainingResult:
    epochs_completed: int
    best_epoch: int
    best_validation_loss: float
    best_validation_accuracy: float
    final_train_loss: float
    stopped_early: bool
    checkpoint_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Trainer:
    """Train a model without console output or retained history."""

    def __init__(
        self,
        *,
        model: BaseModel,
        optimizer: Optimizer,
        loss_fn: nn.Module,
        device: torch.device,
        config: TrainConfig,
        checkpoint_path: Path,
        checkpoint_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.device = device
        self.config = config
        self.checkpoint_path = checkpoint_path
        self.checkpoint_metadata = checkpoint_metadata or {}

    @staticmethod
    def _bounded(loader: DataLoader, maximum: int | None):
        for index, batch in enumerate(loader):
            if maximum is not None and index >= maximum:
                break
            yield batch

    def _training_epoch(self, loader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        total_samples = 0
        amp_enabled = self.config.amp and self.device.type == "cuda"
        scaler = None
        if amp_enabled:
            scaler_class = getattr(torch.amp, "GradScaler", None)
            scaler = (
                scaler_class("cuda")
                if scaler_class is not None
                else torch.cuda.amp.GradScaler()
            )

        for inputs, targets in self._bounded(loader, self.config.max_train_batches):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            self.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=self.device.type, enabled=amp_enabled):
                outputs = self.model(inputs)
                loss = self.loss_fn(outputs, targets)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite training loss")
            if scaler is None:
                loss.backward()
                if self.config.gradient_clip_norm is not None:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), self.config.gradient_clip_norm
                    )
                self.optimizer.step()
            else:
                scaler.scale(loss).backward()
                if self.config.gradient_clip_norm is not None:
                    scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), self.config.gradient_clip_norm
                    )
                scaler.step(self.optimizer)
                scaler.update()
            samples = targets.shape[0]
            total_loss += float(loss.detach()) * samples
            total_samples += samples

        if total_samples == 0:
            raise RuntimeError("training loader produced no samples")
        return total_loss / total_samples

    def _validation(self, loader: DataLoader) -> tuple[float, float]:
        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        with torch.inference_mode():
            for inputs, targets in self._bounded(
                loader, self.config.max_validation_batches
            ):
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                outputs = self.model(inputs)
                loss = self.loss_fn(outputs, targets)
                samples = targets.shape[0]
                total_loss += float(loss) * samples
                total_correct += int((outputs.argmax(dim=1) == targets).sum())
                total_samples += samples
        if total_samples == 0:
            raise RuntimeError("validation loader produced no samples")
        return total_loss / total_samples, total_correct / total_samples

    def _score(self, validation_loss: float, validation_accuracy: float) -> float:
        if self.config.checkpoint_metric == "loss":
            return validation_loss
        if self.config.checkpoint_metric == "accuracy":
            return validation_accuracy
        raise ValueError(
            f"unsupported checkpoint metric: {self.config.checkpoint_metric}"
        )

    def _is_better(self, score: float, best: float) -> bool:
        return score < best if self.config.checkpoint_mode == "min" else score > best

    def _save_checkpoint(self, epoch: int, score: float) -> None:
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.checkpoint_path.with_suffix(self.checkpoint_path.suffix + ".tmp")
        torch.save(
            {
                "model_state": self.model.state_dict(),
                "epoch": epoch,
                "score": score,
                "metadata": self.checkpoint_metadata,
            },
            temp,
        )
        temp.replace(self.checkpoint_path)

    def fit(self, train_loader: DataLoader, validation_loader: DataLoader) -> TrainingResult:
        self.model.to(self.device)
        best_score = math.inf if self.config.checkpoint_mode == "min" else -math.inf
        best_epoch = 0
        best_loss = math.inf
        best_accuracy = 0.0
        final_train_loss = math.inf
        stale_epochs = 0
        epochs_completed = 0
        stopped_early = False

        for epoch in range(1, self.config.epochs + 1):
            final_train_loss = self._training_epoch(train_loader)
            validation_loss, validation_accuracy = self._validation(validation_loader)
            score = self._score(validation_loss, validation_accuracy)
            epochs_completed = epoch
            if self._is_better(score, best_score):
                best_score = score
                best_epoch = epoch
                best_loss = validation_loss
                best_accuracy = validation_accuracy
                stale_epochs = 0
                self._save_checkpoint(epoch, score)
            else:
                stale_epochs += 1

            patience = self.config.early_stopping_patience
            if patience is not None and stale_epochs > patience:
                stopped_early = True
                break

        if best_epoch == 0 or not self.checkpoint_path.is_file():
            raise RuntimeError("training did not produce a best checkpoint")
        return TrainingResult(
            epochs_completed=epochs_completed,
            best_epoch=best_epoch,
            best_validation_loss=best_loss,
            best_validation_accuracy=best_accuracy,
            final_train_loss=final_train_loss,
            stopped_early=stopped_early,
            checkpoint_path=self.checkpoint_path.as_posix(),
        )
