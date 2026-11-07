from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.accept_integrity_audit import accept_integrity_audit
from scripts.build_implementation_review_bundle import (
    build_implementation_review_bundle,
)
from scripts.build_plan_review_bundle import (
    build_plan_review_bundle,
    plan_audit_input_hashes,
)
from scripts.build_review_bundle import build_review_bundle
from scripts.common import sha256_file, sha256_path_set
from scripts.implementation_delta import (
    complete_implementation_delta,
    lock_implementation_delta,
)
from scripts.next_agent_action import next_agent_action
from scripts.records import plan_hash

EXPERIMENT_ID = "EXP-GATE"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _record(profile: str = "balanced") -> str:
    return f"""# {EXPERIMENT_ID}

## Hypothesis

- Research objective: determine whether the method improves useful accuracy
- Study role: feasibility
- Claim: the controlled change improves useful accuracy
- Rationale: it targets a relevant representation
- Alternative explanation: extra capacity causes the gain
- Minimum discriminating evidence: matched evaluation against the baseline
- Falsifier: accuracy does not improve
- Primary metric: test_accuracy maximize
- Diagnostic guardrail: none
- Baseline: none
- Decision mode: threshold
- Minimum meaningful effect: 0.01
- Expected trend: not_applicable
- Trend evidence rule: not_applicable
- Novelty check: a distinct mechanism is tested
- Hypothesis policy check: the plan complies
- Promotion rule: only the primary threshold controls promotion

## Method

- Evidence coverage: readiness now; matched baseline pilot and full comparison before adoption
- Scale justification: two batches check execution only; later stages supply research support
- Implementation: one controlled change
- Baseline behavior: the baseline returns the current representation
- Candidate behavior: the candidate applies one representation change
- Intervention point: src/model.py transform
- Unchanged invariants: data split metric seed and training budget
- Implementation profile: {profile}
- Profile rationale: stable scoped contracts
- Data control: fixed data split and preprocessing
- Training: smoke stage seed 42 with bounded training
- Evaluation: compare the locked primary metric

## Conclusion

- Decision: pending
- Mechanical rule status: pending
- Decision-rule assessment: pending
- Primary result: pending
- Baseline comparison: pending
- Supported scope: pending
- Unsupported or missing evidence: pending
- Confidence and caveats: pending

## Issues and Next Direction

- Main issue: pending
- Next action: pending
- Stop condition: pending
"""


def _base_root(root: Path, *, mode: str, phase: str) -> Path:
    active = root / "experiments/active" / EXPERIMENT_ID
    active.mkdir(parents=True)
    (active / "EXPERIMENT.md").write_text(_record(), encoding="utf-8")
    _write_json(
        active / "SCOPE.json",
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
    config_path = root / f"configs/experiments/{EXPERIMENT_ID}.json"
    _write_json(
        config_path,
        {
            "experiment": {"id": EXPERIMENT_ID, "stage": "smoke"},
            "decision": {
                "primary_metric": "test_accuracy",
                "direction": "maximize",
                "mode": "threshold",
                "minimum_effect": 0.01,
            },
        },
    )
    _write_json(
        root / "research/STATE.json",
        {
            "project_status": "active",
            "active_experiment": EXPERIMENT_ID,
            "phase": phase,
            "stage": "smoke",
            "approvals": {},
            "budgets": {
                "max_scope_files": 10,
                "max_planning_python_reads": 3,
                "max_implementation_entry_python_reads": 3,
                "max_plan_audit_chars": 9000,
                "max_plan_audit_output_words": 250,
                "max_context_chars": 9000,
            },
            "next_action": {"mode": mode, "queue_id": "Q-001"},
        },
    )
    _write_json(
        root / "research/TRAINING_CONTROLS.json",
        {"schema_version": "1.0", "policy": {"reuse": "locked by stage"}},
    )
    (root / "research/GOAL.md").write_text(
        "# Research Goal\n## Question\nDoes useful accuracy improve?\n",
        encoding="utf-8",
    )
    _write_json(root / "experiments/INDEX.json", {"experiments": []})
    manifest = {
        "id": EXPERIMENT_ID,
        "phase": phase,
        "stage": "smoke",
        "queue_id": "Q-001",
        "baseline_id": None,
        "config": f"configs/experiments/{EXPERIMENT_ID}.json",
        "result_dir": f"artifacts/results/{EXPERIMENT_ID}",
        "plan_audit": None,
        "plan_review": {"status": "pending"},
    }
    manifest["plan_sha256"] = plan_hash(
        active / "EXPERIMENT.md",
        config_path,
        active / "SCOPE.json",
    )
    manifest["locked_config_sha256"] = sha256_file(config_path)
    manifest["scope_files"] = []
    if phase != "DRAFT":
        scope = json.loads((active / "SCOPE.json").read_text(encoding="utf-8"))
        _, delta_metadata = lock_implementation_delta(
            root,
            EXPERIMENT_ID,
            _record(),
            scope,
            manifest["config"],
        )
        manifest["implementation_delta"] = delta_metadata
        if phase in {"IMPLEMENTED", "REVIEW_REQUIRED", "READY_TO_FINALIZE"}:
            _, delta_metadata = complete_implementation_delta(
                root,
                active,
                manifest,
            )
            manifest["implementation_delta"] = delta_metadata
    _write_json(active / "MANIFEST.json", manifest)
    return active


def _accept_plan_audit(root: Path, active: Path) -> None:
    manifest = json.loads((active / "MANIFEST.json").read_text(encoding="utf-8"))
    (active / "PLAN_AUDIT.md").write_text(
        "# Accepted Plan Audit\n", encoding="utf-8"
    )
    manifest["plan_audit"] = {
        "verdict": "pass",
        "audit_sha256": sha256_file(active / "PLAN_AUDIT.md"),
        "audited_inputs": plan_audit_input_hashes(root, active, manifest),
    }
    manifest["plan_review"] = {"status": "approved", "source": "human_review"}
    _write_json(active / "MANIFEST.json", manifest)
    state = json.loads((root / "research/STATE.json").read_text(encoding="utf-8"))
    state["approvals"] = {"plan_review_experiment_id": EXPERIMENT_ID}
    _write_json(root / "research/STATE.json", state)


def _completed_plan_audit() -> str:
    return f"""# Plan Audit for {EXPERIMENT_ID}

## Verdict

- Verdict: pass
- Goal-metric alignment: aligned
- Research scale adequacy: readiness only, followed by adequate core comparisons
- Metric gaming path: none identified
- Selection and evaluation separation: separated
- Baseline comparability: comparable
- Metric discipline: one primary metric
- Intervention clarity: one declared baseline-to-candidate change
- Implementation profile fit: balanced is sufficient
- Minimal guardrail: none required

## Required Action

- Blocking issue: none
- Required action: none
"""


def _completed_implementation_audit() -> str:
    return f"""# Implementation Audit for {EXPERIMENT_ID}

## Verdict

- Verdict: pass
- Plan fidelity: implementation follows the locked method
- Data split and leakage: no split handling changed
- Loss and optimization: optimization matches the plan
- Metric implementation: the locked primary metric is used
- Reproducibility and checkpointing: deterministic controls remain active
- Scope and minimality: only the locked files changed
- Declared implementation delta: observed targets match the declaration

## Required Action

- Blocking issue: none
- Required action: none
"""


def _completed_integrity_audit() -> str:
    return f"""# Integrity Audit for {EXPERIMENT_ID}

## Verdict

- Verdict: pass
- Result provenance: aggregate artifacts match the locked run
- Plan adherence: the run follows the locked plan
- Metric validity: the configured primary metric is reported
- Data leakage and split risk: no new leakage path is visible
- Scope discipline: conclusions remain scoped to this run

## Required Action

- Blocking issue: none
- Required action: none
"""


def _copy_template(root: Path, filename: str) -> None:
    source = REPO_ROOT / "experiments/templates" / filename
    target = root / "experiments/templates" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_planning_gate_runs_before_frontier_planner(tmp_path: Path) -> None:
    _base_root(tmp_path, mode="plan_experiment", phase="DRAFT")

    action = next_agent_action(tmp_path, "planning", EXPERIMENT_ID)

    assert action == "action=delegate agent=research_planner"


def test_planning_gate_blocks_setup_placeholders(tmp_path: Path) -> None:
    _base_root(tmp_path, mode="plan_experiment", phase="DRAFT")
    (tmp_path / "research/GOAL.md").write_text(
        "# Research Goal\n<Question>\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="setup placeholders"):
        next_agent_action(tmp_path, "planning", EXPERIMENT_ID)


def test_implementation_gate_returns_locked_profile_agent(tmp_path: Path) -> None:
    active = _base_root(
        tmp_path,
        mode="implement_experiment",
        phase="PLANNED",
    )
    _accept_plan_audit(tmp_path, active)

    action = next_agent_action(tmp_path, "implementation", EXPERIMENT_ID)

    assert action == (
        "action=delegate agent=experiment_implementer profile=balanced"
    )


def test_implementation_gate_blocks_stale_config_before_agent(tmp_path: Path) -> None:
    active = _base_root(
        tmp_path,
        mode="implement_experiment",
        phase="PLANNED",
    )
    _accept_plan_audit(tmp_path, active)
    config_path = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["decision"]["primary_metric"] = "shortcut_accuracy"
    _write_json(config_path, config)

    with pytest.raises(ValueError, match="changed"):
        next_agent_action(tmp_path, "implementation", EXPERIMENT_ID)


def test_plan_audit_gate_builds_delegates_then_accepts_without_retry(
    tmp_path: Path,
) -> None:
    _base_root(
        tmp_path,
        mode="audit_experiment_plan",
        phase="PLANNED",
    )
    template = REPO_ROOT / "experiments/templates/PLAN_AUDIT.md"
    target = tmp_path / "experiments/templates/PLAN_AUDIT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    assert next_agent_action(
        tmp_path, "plan-audit", EXPERIMENT_ID
    ).startswith("action=build ")
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    assert next_agent_action(
        tmp_path, "plan-audit", EXPERIMENT_ID
    ) == "action=delegate agent=plan_auditor"

    (bundle / "PLAN_AUDIT.md").write_text(
        _completed_plan_audit(), encoding="utf-8"
    )
    assert next_agent_action(
        tmp_path, "plan-audit", EXPERIMENT_ID
    ) == "action=accept acceptor=accept_plan_audit"


@pytest.mark.parametrize("value, reason", [
    (None, "malformed-review-output"), ("pending", "partial-review-output"),
])
def test_plan_audit_gate_blocks_missing_scale_without_another_agent(
    tmp_path: Path, value: str | None, reason: str,
) -> None:
    _base_root(tmp_path, mode="audit_experiment_plan", phase="PLANNED")
    _copy_template(tmp_path, "PLAN_AUDIT.md")
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    text = _completed_plan_audit().replace(
        "- Research scale adequacy: readiness only, followed by adequate core comparisons",
        "" if value is None else f"- Research scale adequacy: {value}",
    )
    (bundle / "PLAN_AUDIT.md").write_text(text, encoding="utf-8")
    assert next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID) == (
        f"action=blocked reason={reason}"
    )


def test_plan_audit_gate_rebuilds_stale_bundle_before_agent(tmp_path: Path) -> None:
    _base_root(
        tmp_path,
        mode="audit_experiment_plan",
        phase="PLANNED",
    )
    template = REPO_ROOT / "experiments/templates/PLAN_AUDIT.md"
    target = tmp_path / "experiments/templates/PLAN_AUDIT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    (tmp_path / "research/GOAL.md").write_text(
        "# Research Goal\n## Question\nA changed question.\n",
        encoding="utf-8",
    )

    action = next_agent_action(tmp_path, "plan-audit", EXPERIMENT_ID)

    assert action == "action=build builder=build_plan_review_bundle"


def test_implementation_audit_gate_reuses_completed_output(tmp_path: Path) -> None:
    active = _base_root(
        tmp_path,
        mode="review_implementation",
        phase="IMPLEMENTED",
    )
    state_path = tmp_path / "research/STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["review_policy"] = {"independent_stages": ["pilot", "full"]}
    _write_json(state_path, state)
    manifest_path = active / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stage"] = "pilot"
    manifest["implementation_files"] = []
    manifest["implementation_sha256"] = sha256_path_set(tmp_path, [])
    _write_json(manifest_path, manifest)
    _accept_plan_audit(tmp_path, active)
    _copy_template(tmp_path, "IMPLEMENTATION_AUDIT.md")

    assert next_agent_action(
        tmp_path, "implementation-audit", EXPERIMENT_ID
    ).startswith("action=build ")
    bundle = build_implementation_review_bundle(tmp_path, EXPERIMENT_ID)
    assert next_agent_action(
        tmp_path, "implementation-audit", EXPERIMENT_ID
    ) == "action=delegate agent=evaluator"

    (bundle / "IMPLEMENTATION_AUDIT.md").write_text(
        _completed_implementation_audit(), encoding="utf-8"
    )
    assert next_agent_action(
        tmp_path, "implementation-audit", EXPERIMENT_ID
    ) == "action=accept acceptor=accept_implementation_audit"


def test_integrity_audit_gate_does_not_relaunch_after_acceptance(
    tmp_path: Path,
) -> None:
    active = _base_root(
        tmp_path,
        mode="review_required",
        phase="REVIEW_REQUIRED",
    )
    _accept_plan_audit(tmp_path, active)
    config_path = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    config_hash = sha256_file(config_path)
    _write_json(
        tmp_path / f"artifacts/results/{EXPERIMENT_ID}/metrics.json",
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
        tmp_path / f"artifacts/results/{EXPERIMENT_ID}/manifest.json",
        {"experiment_id": EXPERIMENT_ID, "config_sha256": config_hash},
    )
    _copy_template(tmp_path, "INTEGRITY_AUDIT.md")
    _copy_template(tmp_path, "EVALUATION.md")

    assert next_agent_action(
        tmp_path, "integrity-audit", EXPERIMENT_ID
    ).startswith("action=build ")
    bundle = build_review_bundle(tmp_path, EXPERIMENT_ID)
    assert next_agent_action(
        tmp_path, "integrity-audit", EXPERIMENT_ID
    ) == "action=delegate agent=evaluator"

    (bundle / "INTEGRITY_AUDIT.md").write_text(
        _completed_integrity_audit(), encoding="utf-8"
    )
    assert next_agent_action(
        tmp_path, "integrity-audit", EXPERIMENT_ID
    ) == "action=accept acceptor=accept_integrity_audit"
    accept_integrity_audit(tmp_path, EXPERIMENT_ID)
    assert next_agent_action(
        tmp_path, "integrity-audit", EXPERIMENT_ID
    ) == "action=complete next=evaluation"


def test_agent_facing_skills_require_machine_gate() -> None:
    expected = {
        "plan-experiment": "--task planning",
        "implement-experiment": "--task implementation",
        "audit-experiment-plan": "--task plan-audit",
        "audit-experiment-implementation": "--task implementation-audit",
        "audit-experiment-integrity": "--task integrity-audit",
        "evaluate-experiment": "--task evaluation",
    }
    for skill_name, task in expected.items():
        text = (
            REPO_ROOT / ".agents/skills" / skill_name / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert "scripts/next_agent_action.py" in text
        assert task in text


def test_evaluator_defers_machine_checkable_facts() -> None:
    text = (REPO_ROOT / ".codex/agents/evaluator.toml").read_text(
        encoding="utf-8"
    )

    assert "`DECISION_FACTS.json` as authoritative" in text
    assert "Do not redo hash, file-presence, arithmetic, or schema checks." in text
    assert "without redoing its comparison" in text
