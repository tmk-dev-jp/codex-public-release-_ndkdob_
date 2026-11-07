from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from test_comparison import _raw
from test_record_word_limits import EXPERIMENT_ID, _gate_root, _record

from scripts.accept_evaluation import accept_evaluation
from scripts.accept_integrity_audit import FIELDS, accept_integrity_audit
from scripts.build_human_result_packet import build_human_result_packet
from scripts.build_plan_review_bundle import plan_audit_input_hashes
from scripts.common import atomic_write_json, read_json, sha256_file, sha256_path_set
from scripts.finalize_experiment import finalize_experiment
from scripts.implementation_delta import complete_implementation_delta, lock_implementation_delta
from scripts.records import plan_hash
from scripts.run_experiment import execute_experiment

ROOT = Path(__file__).resolve().parents[2]


def _implemented_group(root: Path, review_mode: str) -> Path:
    active = _gate_root(root, phase="IMPLEMENTED", record=_record())
    (root / "research/GOAL.md").write_text("# Research Goal\n", encoding="utf-8")
    (root / "experiments/DIGEST.md").write_text("# Digest\n", encoding="utf-8")
    state = read_json(root / "research/STATE.json")
    state["execution_policy"] = read_json(ROOT / "research/STATE.json")["execution_policy"]
    atomic_write_json(root / "research/STATE.json", state)
    config = _raw()
    config["experiment"].update(
        id=EXPERIMENT_ID,
        output_dir=f"artifacts/results/{EXPERIMENT_ID}",
        review_mode=review_mode,
    )
    manifest = read_json(active / "MANIFEST.json")
    config_path = root / manifest["config"]
    atomic_write_json(config_path, config)
    scope = {
        "schema_version": "1.3",
        "read_paths": [],
        "write_paths": [],
        "test_paths": [],
        "change_targets": [],
        "planning_reads": [],
        "implementation_entry_reads": [],
    }
    atomic_write_json(active / "SCOPE.json", scope)
    manifest.update(
        record=f"experiments/active/{EXPERIMENT_ID}/EXPERIMENT.md",
        baseline_id=None,
        locked_config_sha256=sha256_file(config_path),
        plan_sha256=plan_hash(active / "EXPERIMENT.md", config_path, active / "SCOPE.json"),
        implementation_files=[],
        implementation_sha256=sha256_path_set(root, []),
    )
    _, manifest["implementation_delta"] = lock_implementation_delta(
        root, EXPERIMENT_ID, _record(), scope, manifest["config"]
    )
    _, manifest["implementation_delta"] = complete_implementation_delta(root, active, manifest)
    (active / "PLAN_AUDIT.md").write_text("# Accepted fixture audit\n", encoding="utf-8")
    manifest["plan_audit"] = {
        "verdict": "pass",
        "audit_sha256": sha256_file(active / "PLAN_AUDIT.md"),
        "audited_inputs": plan_audit_input_hashes(root, active, manifest),
    }
    atomic_write_json(active / "MANIFEST.json", manifest)
    atomic_write_json(
        root / "experiments/INDEX.json",
        {"experiments": [{"id": EXPERIMENT_ID, "stage": "smoke", "record": manifest["record"]}]},
    )
    (root / "experiments/completed").mkdir()
    (root / "review/completed").mkdir(parents=True)
    for relative in (
        "human/templates/HUMAN_RESULTS.md",
        "human/templates/HUMAN_INTERPRETATION.md",
        "experiments/templates/INTEGRITY_AUDIT.md",
        "experiments/templates/EVALUATION.md",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return active


@pytest.mark.parametrize("review_mode", ["local", "independent"])
@pytest.mark.parametrize("tamper", [False, True])
def test_group_execution_through_review_and_finalization(tmp_path, review_mode, tamper):
    import torch

    active = _implemented_group(tmp_path, review_mode)
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        execute_experiment(tmp_path, EXPERIMENT_ID)
    finally:
        torch.set_num_threads(threads)
    facts = read_json(active / "DECISION_FACTS.json")
    assert facts["comparison_design"]["required_runs"] == 8
    status = facts["decision_rule"]["status"]
    output = tmp_path / f"artifacts/results/{EXPERIMENT_ID}"
    results = [output / f"runs/R{i:03d}/metrics.json" for i in range(1, 9)]
    before = [path.read_bytes() for path in results]
    conclusion = f"""## Conclusion

- Decision: inconclusive
- Mechanical rule status: {status}
- Decision-rule assessment: all required runs completed under the fixed rule
- Primary result: see the aggregate and each paired condition
- Baseline comparison: use the internal reference from all eight runs
- Supported scope: workflow readiness on synthetic data only
- Unsupported or missing evidence: research support and independent datasets
- Confidence and caveats: smoke runs do not establish research utility

## Issues and Next Direction

- Main issue: research-scale evidence remains missing
- Next action: plan an adequately powered pilot
- Stop recommendation: stop if essential controls cannot be kept comparable
"""
    if review_mode == "independent":
        bundle = tmp_path / f"review/bundles/{EXPERIMENT_ID}"
        request = read_json(bundle / "INTEGRITY_REQUEST.json")
        assert request["audited_input_hashes"]["comparison_sha256"]
        audit = "# Fixture integrity audit\n\n" + "\n".join(
            f"- {field}: {'pass' if field == 'Verdict' else 'fixture evidence checked'}"
            for field in FIELDS
        )
        (bundle / "INTEGRITY_AUDIT.md").write_text(audit + "\n", encoding="utf-8")
        accept_integrity_audit(tmp_path, EXPERIMENT_ID)
        (bundle / "EVALUATION.md").write_text(conclusion, encoding="utf-8")
        accept_evaluation(tmp_path, EXPERIMENT_ID)
    else:
        plan = (active / "EXPERIMENT.md").read_text(encoding="utf-8").split("## Conclusion")[0]
        (active / "EXPERIMENT.md").write_text(
            plan + conclusion.replace("Stop recommendation:", "Stop condition:"), encoding="utf-8"
        )

    packet = build_human_result_packet(tmp_path, EXPERIMENT_ID)
    human_text = (packet / "RESULTS.md").read_text(encoding="utf-8")
    assert all(f"R{i:03d}" in human_text for i in range(1, 9))
    assert "reference_mean" in human_text
    if tamper:
        metrics = read_json(results[-1])
        metrics["primary_metric"]["value"] += 0.25
        atomic_write_json(results[-1], metrics)
        with pytest.raises(ValueError, match="decision fact inputs"):
            finalize_experiment(tmp_path, EXPERIMENT_ID)
        assert active.is_dir()
        assert read_json(tmp_path / "research/STATE.json")["phase"] == "READY_TO_FINALIZE"
        return

    completed = finalize_experiment(tmp_path, EXPERIMENT_ID)
    state = read_json(tmp_path / "research/STATE.json")
    assert completed.is_dir() and not active.exists()
    assert state["active_experiment"] is None
    assert state["next_action"]["mode"] == "maintain_memory"
    assert [path.read_bytes() for path in results] == before
