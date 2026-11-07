"""Bounded, matched comparisons under one locked experiment hypothesis."""

from __future__ import annotations

import copy
import math
import re
import statistics
from typing import Any

from dl_research.exceptions import ConfigError


def _keys(value: Any, required: set[str], optional: set[str], label: str) -> dict:
    if not isinstance(value, dict) or not required <= value.keys():
        raise ConfigError(f"{label} is missing required fields")
    if value.keys() - required - optional:
        raise ConfigError(f"{label} contains unsupported fields")
    return value


def _positive(value: Any, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{label} must be an integer >= {minimum}")
    return value


def _entries(value: Any, label: str) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{label} must be a non-empty list")
    ids: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            raise ConfigError(f"{label} entries must be objects")
        identity = entry.get("id")
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,23}", identity):
            raise ConfigError(f"{label} IDs must be short lowercase identifiers")
        if identity in ids:
            raise ConfigError(f"{label} contains duplicate ID {identity}")
        ids.add(identity)
        purpose = entry.get("purpose")
        if (
            not isinstance(purpose, str)
            or not purpose.strip()
            or purpose == "pending"
            or "<" in purpose
        ):
            raise ConfigError(f"{label}.{identity} requires a purpose tied to the core claim")
    return value


def validate_comparison(raw: dict) -> dict | None:
    if "comparison" not in raw:
        return None
    design = _keys(
        raw["comparison"],
        {
            "arms",
            "conditions",
            "seeds",
            "primary",
            "aggregation",
            "max_total_batches",
        },
        set(),
        "comparison",
    )
    arms = _entries(design["arms"], "comparison.arms")
    if len(arms) < 2:
        raise ConfigError("comparison requires at least two arms")
    for arm in arms:
        _keys(arm, {"id", "purpose", "model"}, {"loss"}, "comparison arm")
        _keys(arm["model"], {"name", "parameters"}, set(), "comparison arm model")
        if not isinstance(arm["model"]["name"], str) or not arm["model"]["name"].strip():
            raise ConfigError("comparison arm model.name must be non-empty")
        if not isinstance(arm["model"]["parameters"], dict):
            raise ConfigError("comparison arm model.parameters must be an object")
        if "loss" in arm and (not isinstance(arm["loss"], str) or not arm["loss"].strip()):
            raise ConfigError("comparison arm loss must be non-empty")
    for condition in _entries(design["conditions"], "comparison.conditions"):
        _keys(condition, {"id", "purpose", "data_parameters"}, set(), "comparison condition")
        if not isinstance(condition["data_parameters"], dict):
            raise ConfigError("comparison condition data_parameters must be an object")
    seeds = design["seeds"]
    if not isinstance(seeds, list) or not seeds:
        raise ConfigError("comparison.seeds must be a non-empty list")
    for seed in seeds:
        _positive(seed, "comparison seed", minimum=0)
    if len(set(seeds)) != len(seeds):
        raise ConfigError("comparison seeds must be unique")
    primary = _keys(design["primary"], {"candidate", "reference"}, set(), "comparison.primary")
    identities = {arm["id"] for arm in arms}
    if primary["candidate"] not in identities or primary["reference"] not in identities:
        raise ConfigError("primary contrast must name declared arms")
    if primary["candidate"] == primary["reference"]:
        raise ConfigError("primary contrast requires different arms")
    reference = next(arm for arm in arms if arm["id"] == primary["reference"])
    if (
        raw["model"] != reference["model"]
        or reference.get("loss", raw["train"]["loss"]) != raw["train"]["loss"]
    ):
        raise ConfigError("parent model/loss must match the reference arm for calibration")
    if design["aggregation"] != "paired_mean":
        raise ConfigError("comparison.aggregation must be paired_mean")
    if raw["experiment"].get("baseline_id") is not None:
        raise ConfigError("comparison uses an internal reference arm; baseline_id must be null")
    _positive(design["max_total_batches"], "comparison.max_total_batches")
    limits = [
        raw["train"].get("max_train_batches"),
        raw["train"].get("max_validation_batches"),
        raw["test"].get("max_batches"),
    ]
    for limit in limits:
        _positive(limit, "comparison per-run batch limit")
    count = len(arms) * len(design["conditions"]) * len(seeds)
    # Include each run's sanity batch, training, validation and final evaluation.
    per_run = 1 + _positive(raw["train"]["epochs"], "epochs") * sum(limits[:2]) + limits[2]
    if count * per_run > design["max_total_batches"]:
        raise ConfigError("comparison exceeds its locked total batch budget")
    return design


def comparison_size(raw: dict) -> int:
    design = validate_comparison(raw)
    if design is None:
        return 1
    return len(design["arms"]) * len(design["conditions"]) * len(design["seeds"])


def require_comparison_budget(raw: dict, state: dict) -> None:
    if validate_comparison(raw) is not None:
        maximum = int(state.get("budgets", {}).get("max_comparison_runs", 24))
        if comparison_size(raw) > maximum:
            raise ConfigError(f"comparison exceeds max_comparison_runs={maximum}")


def resolved_runs(raw: dict) -> list[tuple[dict, dict]]:
    design = validate_comparison(raw)
    if design is None:
        raise ConfigError("comparison design is missing")
    result = []
    data_seed = raw["data"].get("seed", raw["experiment"]["seed"])
    for condition in design["conditions"]:
        for seed in design["seeds"]:
            for arm in design["arms"]:
                identity = f"R{len(result) + 1:03d}"
                payload = copy.deepcopy(raw)
                del payload["comparison"]
                payload["experiment"]["seed"] = seed
                payload["experiment"]["output_dir"] = (
                    raw["experiment"]["output_dir"].rstrip("/") + f"/runs/{identity}"
                )
                payload["data"]["seed"] = data_seed
                payload["data"]["parameters"].update(condition["data_parameters"])
                payload["model"] = copy.deepcopy(arm["model"])
                payload["train"]["loss"] = arm.get("loss", raw["train"]["loss"])
                result.append(
                    (
                        {
                            "run_id": identity,
                            "arm": arm["id"],
                            "condition": condition["id"],
                            "seed": seed,
                        },
                        payload,
                    )
                )
    return result


def summarize_comparison(raw: dict, rows: list[dict]) -> dict:
    design = validate_comparison(raw)
    expected = [identity for identity, _ in resolved_runs(raw)]
    if len(rows) != len(expected):
        raise ValueError("comparison is incomplete; all preregistered runs are required")
    for row, identity in zip(rows, expected, strict=True):
        if any(row.get(key) != value for key, value in identity.items()):
            raise ValueError("comparison run identity or order differs from the locked design")
        value = row.get("value")
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise ValueError("comparison requires finite results for every run")
    primary = design["primary"]
    values = {(r["arm"], r["condition"], r["seed"]): r["value"] for r in rows}
    sign = 1 if raw["decision"]["direction"] == "maximize" else -1
    contrasts = []
    for condition in design["conditions"]:
        for arm in design["arms"]:
            if arm["id"] == primary["reference"]:
                continue
            effects = [
                sign
                * (
                    values[(arm["id"], condition["id"], seed)]
                    - values[(primary["reference"], condition["id"], seed)]
                )
                for seed in design["seeds"]
            ]
            contrasts.append(
                {
                    "arm": arm["id"],
                    "reference": primary["reference"],
                    "condition": condition["id"],
                    "paired_effects": effects,
                    "mean_effect": statistics.fmean(effects),
                    "stdev_effect": statistics.stdev(effects) if len(effects) > 1 else None,
                }
            )
    means = {
        arm: statistics.fmean(r["value"] for r in rows if r["arm"] == arm)
        for arm in (primary["candidate"], primary["reference"])
    }
    return {
        "aggregation": "paired_mean",
        "primary": primary,
        "runs": rows,
        "contrasts": contrasts,
        "candidate_mean": means[primary["candidate"]],
        "reference_mean": means[primary["reference"]],
        "oriented_effect": sign * (means[primary["candidate"]] - means[primary["reference"]]),
        "seed_count": len(design["seeds"]),
        "condition_count": len(design["conditions"]),
        "complete": True,
        "uncertainty_scope": (
            "Training-seed variation on fixed data; conditions are not independent replicates."
        ),
    }
