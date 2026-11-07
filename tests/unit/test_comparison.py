from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dl_research.config import load_config
from dl_research.exceptions import PolicyError
from dl_research.experiment.comparison import (
    comparison_size,
    require_comparison_budget,
    resolved_runs,
    summarize_comparison,
)
from dl_research.experiment.comparison_artifacts import comparison_results
from dl_research.experiment.comparison_runner import ComparisonRunner
from dl_research.runtime import atomic_write_json, config_sha256
from scripts.build_decision_facts import build_decision_facts, require_current_decision_facts
from scripts.build_plan_review_bundle import build_plan_review_bundle
from scripts.implementation_delta import lock_implementation_delta
from scripts.mark_implemented import mark_implemented
from scripts.next_agent_action import next_agent_action
from scripts.records import plan_hash

ROOT = Path(__file__).resolve().parents[2]
ID = "EXP-COMPARE"


def _raw() -> dict:
    raw = json.loads((ROOT / "configs/templates/smoke.json").read_text(encoding="utf-8"))
    raw["experiment"].update(id=ID, output_dir=f"artifacts/results/{ID}", baseline_id=None)
    raw["train"].update(max_train_batches=1, max_validation_batches=1, epochs=1, device="cpu")
    raw["test"].update(max_batches=1, device="cpu")
    raw["data"].update(batch_size=8)
    raw["data"]["parameters"]["num_samples"] = 64
    model = copy.deepcopy(raw["model"])
    candidate = copy.deepcopy(model)
    candidate["parameters"]["hidden_dims"] = [16]
    raw["comparison"] = {
        "arms": [
            {"id": "reference", "purpose": "matched reference for the core claim", "model": model},
            {"id": "candidate", "purpose": "test the proposed representation", "model": candidate},
        ],
        "conditions": [
            {"id": "clean", "purpose": "primary condition", "data_parameters": {"noise": 0.0}},
            {
                "id": "noisy",
                "purpose": "test robustness of the same mechanism",
                "data_parameters": {"noise": 0.5},
            },
        ],
        "seeds": [11, 22],
        "primary": {"candidate": "candidate", "reference": "reference"},
        "aggregation": "paired_mean",
        "max_total_batches": 32,
    }
    return raw


def _root(root: Path, raw: dict | None = None) -> Path:
    raw = raw or _raw()
    config = root / f"configs/experiments/{ID}.json"
    atomic_write_json(config, raw)
    state = json.loads((ROOT / "research/STATE.json").read_text(encoding="utf-8"))
    state.update(active_experiment=ID, phase="TRAINED", stage="smoke", project_status="active")
    atomic_write_json(root / "research/STATE.json", state)
    atomic_write_json(root / "experiments/INDEX.json", {"experiments": []})
    atomic_write_json(
        root / f"experiments/active/{ID}/MANIFEST.json",
        {
            "id": ID,
            "phase": "TRAINED",
            "stage": "smoke",
            "baseline_id": None,
            "config": config.relative_to(root).as_posix(),
            "result_dir": raw["experiment"]["output_dir"],
            "locked_config_sha256": config_sha256(config),
        },
    )
    return config


class StubRunner:
    calls: list[str] = []
    fail_run: str | None = None

    def __init__(self, path: Path, root: Path):
        self.config = load_config(path)
        self.root = root
        self.output_dir = root / self.config.experiment.output_dir

    @classmethod
    def from_path(cls, path, *, root):
        return cls(path, root)

    def _prepare_output_dir(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sanity(self):
        return {"status": "passed"}

    def cycle(self):
        identity = self.output_dir.name
        type(self).calls.append(identity)
        if identity == type(self).fail_run:
            raise RuntimeError("deliberate run failure")
        value = 0.8 if self.config.model.parameters["hidden_dims"] == [16] else 0.6
        common = {
            "experiment_id": ID,
            "config_sha256": config_sha256(self.config.source_path),
            "review_mode": self.config.experiment.review_mode,
        }
        metric = {
            "name": self.config.decision.primary_metric,
            "value": value,
            "direction": self.config.decision.direction,
            "decision_mode": self.config.decision.mode,
            "minimum_effect": self.config.decision.minimum_effect,
        }
        atomic_write_json(
            self.output_dir / "metrics.json",
            {
                **common,
                "stage": self.config.experiment.stage,
                "status": "completed",
                "primary_metric": metric,
            },
        )
        atomic_write_json(
            self.output_dir / "manifest.json",
            {
                **common,
                "dataset": {
                    "seed": self.config.data.seed,
                    "parameters": self.config.data.parameters,
                },
            },
        )


@pytest.fixture(autouse=True)
def reset_stub():
    StubRunner.calls = []
    StubRunner.fail_run = None


def test_one_hypothesis_expands_to_matched_runs_without_mutating_config():
    raw = _raw()
    before = copy.deepcopy(raw)
    runs = resolved_runs(raw)
    assert comparison_size(raw) == 8
    assert raw == before
    for index in range(0, len(runs), 2):
        reference, candidate = runs[index][1], runs[index + 1][1]
        assert reference["data"] == candidate["data"]
        assert reference["data"]["seed"] == raw["experiment"]["seed"]
        assert reference["train"] == candidate["train"]
        assert reference["test"] == candidate["test"]
        assert reference["experiment"]["seed"] == candidate["experiment"]["seed"]
        assert reference["experiment"]["id"] == ID
        assert "comparison" not in reference


def test_comparison_and_derived_runs_match_config_schema():
    import jsonschema

    schema = json.loads((ROOT / "schemas/experiment-config.schema.json").read_text("utf-8"))
    raw = _raw()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(raw, schema)
    for _, child in resolved_runs(raw):
        jsonschema.validate(child, schema)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r["comparison"].update(max_total_batches=31), "batch budget"),
        (lambda r: r["comparison"].update(seeds=[11, 11]), "unique"),
        (lambda r: r["comparison"].update(aggregation="best_run"), "paired_mean"),
        (lambda r: r["comparison"]["arms"][1].update(id="reference"), "duplicate"),
        (lambda r: r["comparison"]["arms"][1].update(train={"epochs": 100}), "unsupported"),
        (lambda r: r["comparison"]["arms"][1].update(purpose="pending"), "core claim"),
        (lambda r: r["comparison"]["primary"].update(reference="missing"), "declared arms"),
        (lambda r: r["experiment"].update(baseline_id="EXP-OTHER"), "internal reference"),
        (lambda r: r["train"].update(max_train_batches=None), "batch limit"),
    ],
)
def test_invalid_comparisons_fail_mechanically(mutation, message):
    raw = _raw()
    mutation(raw)
    with pytest.raises(ValueError, match=message):
        resolved_runs(raw)


def test_global_run_limit_and_full_approval_apply_before_execution(tmp_path):
    raw = _raw()
    with pytest.raises(ValueError, match="max_comparison_runs=7"):
        require_comparison_budget(raw, {"budgets": {"max_comparison_runs": 7}})
    raw["experiment"].update(stage="full", review_mode="independent")
    config = _root(tmp_path, raw)
    with pytest.raises(PolicyError, match="full training requires"):
        ComparisonRunner(StubRunner(config, tmp_path))
    assert not StubRunner.calls


def test_all_required_runs_are_executed_and_jointly_evaluated(tmp_path):
    config = _root(tmp_path)
    runner = ComparisonRunner(StubRunner(config, tmp_path))
    result = runner.cycle()
    assert StubRunner.calls == [f"R{i:03d}" for i in range(1, 9)]
    assert result["comparison"]["complete"]
    assert result["comparison"]["oriented_effect"] == pytest.approx(0.2)
    assert len(result["comparison"]["contrasts"]) == 2
    facts = json.loads(build_decision_facts(tmp_path, ID).read_text(encoding="utf-8"))
    assert facts["decision_rule"]["status"] == "met"
    assert facts["comparison_design"]["required_runs"] == 8
    # Recover completed routing without another training call.
    assert runner.cycle() == result
    assert len(StubRunner.calls) == 8


def test_trend_comparison_remains_a_scientific_interpretation(tmp_path):
    raw = _raw()
    raw["decision"].update(mode="trend", minimum_effect=None)
    config = _root(tmp_path, raw)
    ComparisonRunner(StubRunner(config, tmp_path)).cycle()
    facts = json.loads(build_decision_facts(tmp_path, ID).read_text(encoding="utf-8"))
    assert facts["decision_rule"]["status"] == "trend_requires_interpretation"
    assert facts["comparison"]["oriented_effect"] == pytest.approx(0.2)


def test_failure_stops_without_retry_or_discarding_completed_evidence(tmp_path):
    config = _root(tmp_path)
    StubRunner.fail_run = "R003"
    runner = ComparisonRunner(StubRunner(config, tmp_path))
    with pytest.raises(RuntimeError, match="deliberate"):
        runner.cycle()
    assert StubRunner.calls == ["R001", "R002", "R003"]
    output = tmp_path / f"artifacts/results/{ID}"
    assert (output / "runs/R001/metrics.json").is_file()
    assert not (output / "metrics.json").exists()
    with pytest.raises(ValueError, match="no implicit retry"):
        runner.cycle()
    with pytest.raises(FileNotFoundError):
        build_decision_facts(tmp_path, ID)
    assert len(StubRunner.calls) == 3


@pytest.mark.parametrize("action", ["missing", "tampered", "config", "aggregate", "dataset"])
def test_missing_or_changed_run_invalidates_joint_evidence(tmp_path, action):
    config = _root(tmp_path)
    ComparisonRunner(StubRunner(config, tmp_path)).cycle()
    build_decision_facts(tmp_path, ID)
    output = tmp_path / f"artifacts/results/{ID}"
    if action == "missing":
        (output / "runs/R001/metrics.json").unlink()
    else:
        path = {
            "tampered": output / "runs/R001/metrics.json",
            "config": output / "runs/R001/config.json",
            "aggregate": output / "metrics.json",
            "dataset": output / "runs/R002/manifest.json",
        }[action]
        payload = json.loads(path.read_text(encoding="utf-8"))
        if action in {"tampered", "aggregate"}:
            payload["primary_metric"]["value"] = 0.999
        elif action == "config":
            payload["data"]["batch_size"] = 100
        else:
            payload["dataset"]["seed"] = 999
        atomic_write_json(path, payload)
    active = tmp_path / f"experiments/active/{ID}"
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    with pytest.raises((ValueError, FileNotFoundError)):
        comparison_results(tmp_path, config)
    with pytest.raises(ValueError, match="decision fact inputs"):
        require_current_decision_facts(tmp_path, active, manifest)


def test_incomplete_or_best_only_rows_cannot_be_summarized():
    raw = _raw()
    rows = [{**identity, "value": 0.5} for identity, _ in resolved_runs(raw)]
    with pytest.raises(ValueError, match="all preregistered"):
        summarize_comparison(raw, rows[1:])
    rows[0]["value"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        summarize_comparison(raw, rows)


def test_training_seed_repeats_cannot_change_the_condition_dataset(tmp_path):
    config = _root(tmp_path)
    ComparisonRunner(StubRunner(config, tmp_path)).cycle()
    for run_id in ("R003", "R004"):
        path = tmp_path / f"artifacts/results/{ID}/runs/{run_id}/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["dataset"]["seed"] = 999
        atomic_write_json(path, manifest)
    with pytest.raises(ValueError, match="training seeds used different dataset"):
        comparison_results(tmp_path, config, verify_aggregate=False)


def test_group_plan_audit_is_compact_and_budget_checked_before_agent(tmp_path):
    from test_plan_audit import EXPERIMENT_ID
    from test_plan_audit import _root as audit_root

    active = audit_root(tmp_path)
    raw = _raw()
    raw["experiment"].update(id=EXPERIMENT_ID, output_dir=f"artifacts/results/{EXPERIMENT_ID}")
    config = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    atomic_write_json(config, raw)
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    scope = json.loads((active / "SCOPE.json").read_text(encoding="utf-8"))
    record = (active / "EXPERIMENT.md").read_text(encoding="utf-8")
    _, delta = lock_implementation_delta(tmp_path, EXPERIMENT_ID, record, scope, manifest["config"])
    manifest.update(
        implementation_delta=delta,
        locked_config_sha256=config_sha256(config),
        plan_sha256=plan_hash(active / "EXPERIMENT.md", config, active / "SCOPE.json"),
    )
    atomic_write_json(active / "MANIFEST.json", manifest)
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    request = json.loads((bundle / "PLAN_AUDIT_REQUEST.json").read_text(encoding="utf-8"))
    assert request["config"]["comparison"] == raw["comparison"]
    assert (
        sum(
            len((bundle / name).read_text(encoding="utf-8"))
            for name in ("PLAN_AUDIT_REQUEST.json", "PLAN_AUDIT.md")
        )
        <= 9000
    )
    state_path = tmp_path / "research/STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["budgets"]["max_comparison_runs"] = 7
    atomic_write_json(state_path, state)
    with pytest.raises(ValueError, match="max_comparison_runs"):
        build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    with pytest.raises(ValueError, match="max_comparison_runs"):
        next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID)


def test_reimplementation_cannot_erase_recorded_comparison(tmp_path):
    from test_records import _record

    config = _root(tmp_path)
    ComparisonRunner(StubRunner(config, tmp_path)).cycle()
    active = tmp_path / f"experiments/active/{ID}"
    (active / "EXPERIMENT.md").write_text(_record("novel mechanism"), encoding="utf-8")
    atomic_write_json(active / "SCOPE.json", {})
    manifest_path, state_path = active / "MANIFEST.json", tmp_path / "research/STATE.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        phase="FAILED",
        plan_sha256=plan_hash(active / "EXPERIMENT.md", config, active / "SCOPE.json"),
    )
    atomic_write_json(manifest_path, manifest)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["phase"] = "FAILED"
    atomic_write_json(state_path, state)
    metrics = tmp_path / f"artifacts/results/{ID}/metrics.json"
    before = metrics.read_bytes()
    with pytest.raises(ValueError, match="do not erase"):
        mark_implemented(tmp_path, ID)
    assert metrics.read_bytes() == before


def test_config_and_mechanical_gate_do_not_import_torch():
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from dl_research.config import load_config; "
            "from scripts.next_agent_action import next_agent_action; "
            "assert 'torch' not in sys.modules",
        ],
        env=environment,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_real_cpu_comparison_keeps_paired_data_and_all_results(tmp_path):
    import torch

    from dl_research.experiment.runner import ExperimentRunner

    config = _root(tmp_path)
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        result = ExperimentRunner.from_path(config, root=tmp_path).cycle()
    finally:
        torch.set_num_threads(threads)
    summary, artifacts = comparison_results(tmp_path, config)
    assert len(artifacts) == 8
    assert summary == result["comparison"]
    assert summary["seed_count"] == 2
    assert (tmp_path / f"artifacts/results/{ID}/runs/R008/best.pt").is_file()
    assert build_decision_facts(tmp_path, ID).is_file()
