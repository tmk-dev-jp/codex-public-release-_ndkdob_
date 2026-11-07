from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dl_research.experiment.comparison_artifacts import comparison_input_hash, comparison_results
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)
from scripts.records import field, research_focus, section
from scripts.workflow import experiment_manifest_path, require_active

FACTS_FILENAME = "DECISION_FACTS.json"
ALLOWED_PHASES = {"TRAINED", "REVIEW_REQUIRED", "READY_TO_FINALIZE"}


class DecisionFactsRequiredError(ValueError):
    pass


def _payload_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def load_baseline_payload(root: Path, baseline_id: str | None) -> dict[str, Any]:
    if baseline_id is None:
        return {"status": "not_configured", "baseline_id": None}

    index = read_json(root / "experiments/INDEX.json")
    for item in index.get("experiments", []):
        if item.get("id") != baseline_id:
            continue
        if item.get("status") == "aborted":
            raise ValueError("an aborted experiment cannot supply baseline evidence")
        candidate = item.get("metrics")
        if isinstance(candidate, str):
            path = safe_relative_path(root, candidate, allow_missing=True)
            if path.is_file():
                return read_json(path)
        break

    fallback = root / "artifacts/results" / baseline_id / "metrics.json"
    if fallback.is_file():
        return read_json(fallback)
    return {"status": "missing", "baseline_id": baseline_id}


def decision_fact_input_hashes(
    root: Path,
    manifest: dict[str, Any],
) -> dict[str, str]:
    result_dir = root / manifest["result_dir"]
    baseline = load_baseline_payload(root, manifest.get("baseline_id"))
    hashes = {
        "research_focus_sha256": _payload_hash(_research_focus(root, manifest)),
        "config_sha256": sha256_file(root / manifest["config"]),
        "metrics_sha256": sha256_file(result_dir / "metrics.json"),
        "baseline_sha256": _payload_hash(baseline),
    }
    comparison_hash = comparison_input_hash(root, root / manifest["config"])
    if comparison_hash is not None:
        hashes["comparison_sha256"] = comparison_hash
    return hashes


def _research_focus(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    goal = root / "research/GOAL.md"
    record = root / "experiments/active" / manifest["id"] / "EXPERIMENT.md"
    return research_focus(
        goal.read_text(encoding="utf-8") if goal.is_file() else "",
        record.read_text(encoding="utf-8") if record.is_file() else "",
    )


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _primary_metric(payload: dict[str, Any], label: str) -> dict[str, Any]:
    metric = payload.get("primary_metric")
    if not isinstance(metric, dict):
        raise ValueError(f"{label} primary_metric is missing")
    return metric


def build_decision_facts(root: Path, experiment_id: str) -> Path:
    _, manifest = require_active(root, experiment_id, ALLOWED_PHASES)
    config_path = root / manifest["config"]
    config_hash = sha256_file(config_path)
    if config_hash != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    config = read_json(config_path)
    experiment = config.get("experiment")
    if not isinstance(experiment, dict) or experiment.get("id") != experiment_id:
        raise ValueError("config experiment ID does not match")
    baseline_id = experiment.get("baseline_id")
    if manifest.get("baseline_id") != baseline_id:
        raise ValueError("manifest baseline does not match locked config")
    metrics = read_json(root / manifest["result_dir"] / "metrics.json")
    if metrics.get("experiment_id") != experiment_id:
        raise ValueError("metrics experiment ID does not match")
    if metrics.get("config_sha256") != config_hash:
        raise ValueError("metrics config hash does not match locked config")
    if metrics.get("baseline_id") != baseline_id:
        raise ValueError("metrics baseline does not match locked config")
    if metrics.get("status") != "completed":
        raise ValueError("metrics status is not completed")

    decision = config.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("config decision is missing")
    metric = _primary_metric(metrics, "current")
    expected_name = decision.get("primary_metric")
    direction = decision.get("direction")
    mode = decision.get("mode")
    minimum_effect = decision.get("minimum_effect")
    if metric.get("name") != expected_name:
        raise ValueError("metrics primary metric does not match locked config")
    if metric.get("direction") != direction:
        raise ValueError("metrics direction does not match locked config")
    if metric.get("decision_mode") != mode:
        raise ValueError("metrics decision mode does not match locked config")
    if metric.get("minimum_effect") != minimum_effect:
        raise ValueError("metrics minimum effect does not match locked config")
    if direction not in {"maximize", "minimize"}:
        raise ValueError("decision direction must be maximize or minimize")
    if mode not in {"threshold", "trend"}:
        raise ValueError("decision mode must be threshold or trend")

    current_value = _number(metric.get("value"), "current metric value")
    baseline = load_baseline_payload(root, baseline_id)
    baseline_metric = baseline.get("primary_metric")
    baseline_value: float | None = None
    comparison_status = "baseline_unavailable"
    oriented_effect: float | None = None
    comparison_summary = None
    if "comparison" in config:
        comparison_summary, _ = comparison_results(root, config_path)
        baseline_value = comparison_summary["reference_mean"]
        oriented_effect = comparison_summary["oriented_effect"]
        comparison_status = "available"
    elif isinstance(baseline_metric, dict):
        if baseline_metric.get("name") != expected_name:
            raise ValueError("baseline primary metric does not match locked config")
        if baseline_metric.get("direction") != direction:
            raise ValueError("baseline metric direction does not match locked config")
        baseline_value = _number(
            baseline_metric.get("value"),
            "baseline metric value",
        )
        comparison_status = "available"
        oriented_effect = (
            current_value - baseline_value
            if direction == "maximize"
            else baseline_value - current_value
        )

    if mode == "trend":
        if minimum_effect is not None:
            raise ValueError("trend mode minimum effect must be null")
        rule_status = "trend_requires_interpretation"
    elif comparison_status != "available":
        _number(minimum_effect, "minimum effect")
        rule_status = "baseline_unavailable"
    else:
        threshold = _number(minimum_effect, "minimum effect")
        meets_threshold = oriented_effect >= threshold or math.isclose(
            oriented_effect,
            threshold,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        rule_status = "met" if meets_threshold else "not_met"

    facts = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "research_focus": _research_focus(root, manifest),
        "metric": {
            "name": expected_name,
            "direction": direction,
            "current_value": current_value,
            "baseline_id": baseline_id,
            "baseline_value": baseline_value,
        },
        "comparison": {
            "status": comparison_status,
            "oriented_effect": oriented_effect,
            "positive_means": "improvement",
        },
        "decision_rule": {
            "mode": mode,
            "minimum_effect": minimum_effect,
            "status": rule_status,
        },
        "inputs": decision_fact_input_hashes(root, manifest),
    }
    if comparison_summary is not None:
        facts["comparison_design"] = {
            "primary": comparison_summary["primary"],
            "aggregation": comparison_summary["aggregation"],
            "contrasts": comparison_summary["contrasts"],
            "required_runs": len(comparison_summary["runs"]),
            "uncertainty_scope": comparison_summary["uncertainty_scope"],
        }
    active = root / "experiments/active" / experiment_id
    path = active / FACTS_FILENAME
    atomic_write_json(path, facts)
    manifest["decision_facts"] = {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "inputs": facts["inputs"],
        "rule_status": rule_status,
    }
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)
    return path


def require_current_decision_facts(
    root: Path,
    active: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    metadata = manifest.get("decision_facts")
    path = active / FACTS_FILENAME
    if not isinstance(metadata, dict) or not path.is_file():
        raise DecisionFactsRequiredError("current decision facts are required")
    if metadata.get("sha256") != sha256_file(path):
        raise DecisionFactsRequiredError("decision facts changed after generation")
    try:
        current_inputs = decision_fact_input_hashes(root, manifest)
        facts = read_json(path)
    except (OSError, KeyError, ValueError) as exc:
        raise DecisionFactsRequiredError(
            "decision fact inputs are unavailable"
        ) from exc
    if metadata.get("inputs") != current_inputs:
        raise DecisionFactsRequiredError("decision fact inputs changed")
    if facts.get("experiment_id") != manifest.get("id"):
        raise DecisionFactsRequiredError("decision facts experiment ID differs")
    if facts.get("decision_rule", {}).get("status") != metadata.get("rule_status"):
        raise DecisionFactsRequiredError("decision facts status differs from manifest")
    return facts


def require_record_decision_status(record_text: str, facts: dict[str, Any]) -> None:
    conclusion = section(record_text, "## Conclusion")
    recorded = field(conclusion, "Mechanical rule status").lower()
    expected = str(facts["decision_rule"]["status"]).lower()
    if recorded != expected:
        raise ValueError(
            f"Mechanical rule status must be {expected}; found {recorded}"
        )


def _execute() -> str:
    parser = QuietArgumentParser(description="Build deterministic decision facts.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    path = build_decision_facts(root, args.experiment_id)
    facts = read_json(path)
    return (
        f"{path.relative_to(root).as_posix()} "
        f"status={facts['decision_rule']['status']}"
    )


if __name__ == "__main__":
    raise SystemExit(run_script("build-decision-facts", _execute))
