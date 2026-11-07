from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_context import build_context
from scripts.build_decision_facts import build_decision_facts
from scripts.build_plan_review_bundle import plan_audit_input_hashes
from scripts.common import sha256_file, sha256_path_set
from scripts.finalize_experiment import finalize_experiment
from scripts.implementation_delta import (
    complete_implementation_delta,
    lock_implementation_delta,
)
from scripts.lock_plan import lock_plan
from scripts.records import conclusion_word_count, plan_hash, plan_word_count

EXPERIMENT_ID = "EXP-LIMIT"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _words(count: int) -> str:
    return " ".join(["detail"] * count)


def _record(*, plan_extra: int = 0, conclusion_extra: int = 0) -> str:
    rationale = _words(plan_extra) if plan_extra else "a concise mechanism"
    caveats = _words(conclusion_extra) if conclusion_extra else "pilot evidence only"
    return f"""# {EXPERIMENT_ID}

## Hypothesis

- Research objective: determine whether the method improves useful accuracy
- Study role: feasibility
- Claim: a measurable prediction
- Rationale: {rationale}
- Alternative explanation: the gain comes from extra capacity
- Minimum discriminating evidence: matched-capacity baseline comparison
- Falsifier: a result that reverses the expected effect
- Primary metric: test_accuracy maximize
- Diagnostic guardrail: none
- Baseline: none
- Decision mode: threshold
- Minimum meaningful effect: 0.01
- Expected trend: not_applicable
- Trend evidence rule: not_applicable
- Novelty check: tests a distinct mechanism rather than replaying the baseline
- Hypothesis policy check: complies with the configured hypothesis policy
- Promotion rule: promote only when the locked threshold is met

## Method

- Evidence coverage: readiness now; matched pilot and full comparison before adoption
- Scale justification: two batches check execution only; later stages supply research support
- Implementation: one controlled implementation change
- Baseline behavior: the current model uses the baseline representation
- Candidate behavior: the candidate changes one representation step
- Intervention point: src/model.py transform
- Unchanged invariants: dataset split metric seed and training budget
- Implementation profile: balanced
- Profile rationale: stable contracts and two scoped paths
- Data control: fixed dataset version split and preprocessing
- Training: smoke stage seed 42 loss checkpoint and bounded budget
- Evaluation: compare the primary metric with the locked decision rule

## Conclusion

- Decision: support
- Mechanical rule status: baseline_unavailable
- Decision-rule assessment: the locked threshold was met
- Primary result: test accuracy improved by 0.02
- Baseline comparison: improvement exceeded the minimum effect
- Supported scope: this dataset split seed and smoke stage
- Unsupported or missing evidence: other datasets splits seeds and larger stages
- Confidence and caveats: {caveats}

## Issues and Next Direction

- Main issue: robustness remains unknown
- Next action: run one preregistered pilot
- Stop condition: stop this branch if the effect reverses
"""


def _gate_root(root: Path, *, phase: str, record: str) -> Path:
    active = root / "experiments/active" / EXPERIMENT_ID
    active.mkdir(parents=True)
    (active / "EXPERIMENT.md").write_text(record, encoding="utf-8")
    _write_json(
        root / "research/STATE.json",
        {
            "project_id": "limit-test",
            "project_status": "active",
            "active_experiment": EXPERIMENT_ID,
            "phase": phase,
            "stage": "smoke",
            "review_required": False,
            "latest_completed_experiment": None,
            "baseline_experiment": None,
            "approvals": {},
            "budgets": {
                "max_experiment_plan_words": 700,
                "max_experiment_conclusion_words": 400,
                "max_context_chars": 9000,
                "max_completed_digest_rows": 20,
            },
            "next_action": {"mode": phase.lower(), "queue_id": "Q-001"},
        },
    )
    _write_json(
        root / "research/TRAINING_CONTROLS.json",
        {"schema_version": "1.0", "policy": {"reuse": "locked by stage"}},
    )
    _write_json(
        active / "MANIFEST.json",
        {
            "id": EXPERIMENT_ID,
            "stage": "smoke",
            "status": "active",
            "phase": phase,
            "queue_id": "Q-001",
            "config": f"configs/experiments/{EXPERIMENT_ID}.json",
            "result_dir": f"artifacts/results/{EXPERIMENT_ID}",
        },
    )
    return active


def test_lock_plan_blocks_smoke_research_claim_without_state_changes(tmp_path: Path) -> None:
    record = _record().replace("Study role: feasibility", "Study role: core")
    active = _gate_root(tmp_path, phase="DRAFT", record=record)
    paths = [active / "MANIFEST.json", tmp_path / "research/STATE.json"]
    before = [path.read_bytes() for path in paths]
    with pytest.raises(ValueError, match="smoke requires Study role feasibility"):
        lock_plan(tmp_path, EXPERIMENT_ID)
    assert [path.read_bytes() for path in paths] == before
    assert not (active / "IMPLEMENTATION_DELTA.json").exists()


def test_lock_plan_rejects_hypothesis_and_method_over_700_words(
    tmp_path: Path,
) -> None:
    _gate_root(tmp_path, phase="DRAFT", record=_record(plan_extra=700))

    with pytest.raises(
        ValueError, match=r"Hypothesis \+ Method exceeds 700 words"
    ):
        lock_plan(tmp_path, EXPERIMENT_ID)


def test_finalize_rejects_conclusion_and_issues_over_400_words(
    tmp_path: Path,
) -> None:
    _gate_root(
        tmp_path,
        phase="READY_TO_FINALIZE",
        record=_record(conclusion_extra=400),
    )

    with pytest.raises(
        ValueError, match=r"Conclusion \+ Issues exceeds 400 words"
    ):
        finalize_experiment(tmp_path, EXPERIMENT_ID)


@pytest.mark.parametrize("formatted", [False, True])
def test_finalize_accepts_record_over_500_total_words_within_section_limits(
    tmp_path: Path, formatted: bool,
) -> None:
    record = _record(plan_extra=360, conclusion_extra=180)
    if formatted:
        from test_presentation_recovery import _formatted

        record = _formatted(record)
    assert len(record.split()) > 500
    assert plan_word_count(record) <= 700
    assert conclusion_word_count(record) <= 400
    active = _gate_root(tmp_path, phase="READY_TO_FINALIZE", record=record)

    config_path = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    config = json.loads(
        (REPO_ROOT / "configs/templates/smoke.json").read_text(encoding="utf-8")
    )
    config["experiment"].update(
        {
            "id": EXPERIMENT_ID,
            "output_dir": f"artifacts/results/{EXPERIMENT_ID}",
            "queue_id": "Q-001",
        }
    )
    _write_json(config_path, config)
    scope_path = active / "SCOPE.json"
    _write_json(
        scope_path,
        {
            "schema_version": "1.3",
            "read_paths": [],
            "write_paths": [],
            "test_paths": [],
            "change_targets": [],
            "planning_reads": [],
            "implementation_entry_reads": [],
        },
    )

    config_hash = sha256_file(config_path)
    implementation_hash = sha256_path_set(tmp_path, [])
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest.update(
        {
            "baseline_id": None,
            "record": f"experiments/active/{EXPERIMENT_ID}/EXPERIMENT.md",
            "scope": f"experiments/active/{EXPERIMENT_ID}/SCOPE.json",
            "plan_sha256": plan_hash(
                active / "EXPERIMENT.md", config_path, scope_path
            ),
            "locked_config_sha256": config_hash,
            "implementation_sha256": implementation_hash,
            "implementation_files": [],
            "integrity_audit": None,
            "evaluation": None,
        }
    )
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    _, delta_metadata = lock_implementation_delta(
        tmp_path,
        EXPERIMENT_ID,
        record,
        scope,
        manifest["config"],
    )
    manifest["implementation_delta"] = delta_metadata
    _, delta_metadata = complete_implementation_delta(
        tmp_path,
        active,
        manifest,
    )
    manifest["implementation_delta"] = delta_metadata
    _write_json(active / "MANIFEST.json", manifest)

    result_dir = tmp_path / f"artifacts/results/{EXPERIMENT_ID}"
    _write_json(
        result_dir / "metrics.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "baseline_id": None,
            "status": "completed",
            "config_sha256": config_hash,
            "primary_metric": {
                "name": "test_accuracy",
                "value": 0.72,
                "direction": "maximize",
                "decision_mode": "threshold",
                "minimum_effect": 0.01,
            },
        },
    )
    _write_json(
        result_dir / "manifest.json",
        {"implementation_sha256": implementation_hash},
    )
    (tmp_path / "experiments/completed").mkdir(parents=True)
    _write_json(
        tmp_path / "experiments/INDEX.json",
        {
            "experiments": [
                {
                    "id": EXPERIMENT_ID,
                    "stage": "smoke",
                    "status": "active",
                    "phase": "READY_TO_FINALIZE",
                    "record": manifest["record"],
                }
            ]
        },
    )
    (tmp_path / "research/GOAL.md").write_text(
        "# Research Goal\n", encoding="utf-8"
    )
    (tmp_path / "experiments/DIGEST.md").write_text(
        "# Completed Experiment Digest\n", encoding="utf-8"
    )
    (active / "PLAN_AUDIT.md").write_text(
        "# Accepted Plan Audit\n", encoding="utf-8"
    )
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest["plan_audit"] = {
        "verdict": "pass",
        "audit_sha256": sha256_file(active / "PLAN_AUDIT.md"),
        "audited_inputs": plan_audit_input_hashes(tmp_path, active, manifest),
    }
    _write_json(active / "MANIFEST.json", manifest)
    build_decision_facts(tmp_path, EXPERIMENT_ID)

    completed = finalize_experiment(tmp_path, EXPERIMENT_ID)

    assert completed == tmp_path / f"experiments/completed/{EXPERIMENT_ID}"
    assert completed.is_dir()
    assert not active.exists()


def test_generated_context_respects_9000_character_limit(tmp_path: Path) -> None:
    record = _record().replace("a concise mechanism", "x" * 12_000)
    _gate_root(tmp_path, phase="DRAFT", record=record)
    (tmp_path / "research/GOAL.md").write_text(
        "# Research Goal\n## Question\nA bounded question.\n", encoding="utf-8"
    )
    (tmp_path / "experiments/DIGEST.md").write_text(
        "# Completed Experiment Digest\n", encoding="utf-8"
    )

    context = build_context(tmp_path).read_text(encoding="utf-8")

    assert len(context) <= 9000
    assert context.endswith("[Context truncated by configured limit.]\n")
