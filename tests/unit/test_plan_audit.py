from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.accept_plan_audit import accept_plan_audit
from scripts.build_plan_review_bundle import (
    PlanAuditRequiredError,
    build_plan_review_bundle,
    require_accepted_plan_audit,
)
from scripts.common import sha256_file
from scripts.implementation_delta import lock_implementation_delta
from scripts.lock_plan import lock_plan
from scripts.records import plan_hash

EXPERIMENT_ID = "EXP-AUDIT"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _record() -> str:
    return f"""# {EXPERIMENT_ID}

## Hypothesis

- Research objective: determine whether the method improves target capability
- Study role: feasibility
- Claim: accuracy reflects the target capability
- Rationale: the intervention should improve useful representations
- Alternative explanation: selection exploits a nuisance correlation
- Minimum discriminating evidence: matched evaluation plus the locked guardrail
- Falsifier: accuracy rises while the guardrail degrades
- Primary metric: test_accuracy maximize
- Diagnostic guardrail: nuisance accuracy, diagnostic only
- Baseline: none
- Decision mode: threshold
- Minimum meaningful effect: 0.01
- Expected trend: not_applicable
- Trend evidence rule: not_applicable
- Novelty check: tests a distinct mechanism
- Hypothesis policy check: complies with policy
- Promotion rule: primary threshold only

## Method

- Evidence coverage: readiness now; matched pilot and representative full comparison before adoption
- Scale justification: two batches check execution only; later comparisons supply research evidence
- Implementation: one controlled representation change
- Baseline behavior: transform returns the current representation
- Candidate behavior: transform applies one controlled representation change
- Intervention point: src/change.py transform
- Unchanged invariants: data split metric seed and training budget
- Implementation profile: balanced
- Profile rationale: stable contracts and two scoped paths
- Data control: fixed split and preprocessing
- Training: smoke seed 17 and loss checkpoint
- Evaluation: locked final split and primary metric

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


def _audit(verdict: str = "pass", extra: str = "") -> str:
    return f"""# Plan Audit for {EXPERIMENT_ID}

## Verdict

- Verdict: {verdict}
- Goal-metric alignment: aligned with the stated capability
- Research scale adequacy: readiness; core comparisons required before claiming research support
- Metric gaming path: nuisance selection could raise accuracy alone
- Selection and evaluation separation: final evidence is held out
- Baseline comparability: direction population and budget match
- Metric discipline: one primary metric controls promotion
- Intervention clarity: one baseline-to-candidate intervention is isolated
- Implementation profile fit: balanced matches the scoped risk
- Minimal guardrail: report nuisance accuracy diagnostically only

## Required Action

- Blocking issue: none
- Required action: preserve the diagnostic-only guardrail
{extra}
"""


def _root(root: Path, *, max_chars: int = 9000) -> Path:
    active = root / "experiments/active" / EXPERIMENT_ID
    active.mkdir(parents=True)
    (active / "EXPERIMENT.md").write_text(_record(), encoding="utf-8")
    source = root / "src/change.py"
    source.parent.mkdir(parents=True)
    source.write_text("def transform(value):\n    return value\n", encoding="utf-8")
    scope = {
        "schema_version": "1.3",
        "read_paths": [],
        "write_paths": ["src/change.py"],
        "test_paths": [],
        "change_targets": [
            {
                "path": "src/change.py",
                "role": "intervention",
                "action": "modify",
                "symbols": ["transform"],
            }
        ],
        "planning_reads": [],
        "implementation_entry_reads": [],
    }
    _write_json(active / "SCOPE.json", scope)
    config_path = root / f"configs/experiments/{EXPERIMENT_ID}.json"
    _write_json(
        config_path,
        {
            "data": {"batch_size": 32},
            "train": {"optimizer": {"learning_rate": 0.01}},
            "evaluation": {"primary_metric": "test_accuracy"},
        },
    )
    _write_json(
        root / "research/TRAINING_CONTROLS.json",
        {"schema_version": "1.0", "policy": {"reuse": "locked by stage"}},
    )
    (root / "research/GOAL.md").write_text(
        "# Research Goal\n## Question\nDoes the capability improve?\n",
        encoding="utf-8",
    )
    template = REPO_ROOT / "experiments/templates/PLAN_AUDIT.md"
    target = root / "experiments/templates/PLAN_AUDIT.md"
    target.parent.mkdir(parents=True)
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    manifest = {
        "id": EXPERIMENT_ID,
        "phase": "PLANNED",
        "queue_id": "Q-001",
        "baseline_id": None,
        "config": f"configs/experiments/{EXPERIMENT_ID}.json",
        "plan_audit": None,
    }
    manifest["plan_sha256"] = plan_hash(
        active / "EXPERIMENT.md", config_path, active / "SCOPE.json"
    )
    manifest["locked_config_sha256"] = sha256_file(config_path)
    _, delta_metadata = lock_implementation_delta(
        root,
        EXPERIMENT_ID,
        _record(),
        scope,
        manifest["config"],
    )
    manifest["implementation_delta"] = delta_metadata
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(
        root / "research/STATE.json",
        {
            "project_id": "audit-test",
            "project_status": "active",
            "active_experiment": EXPERIMENT_ID,
            "phase": "PLANNED",
            "stage": "smoke",
            "budgets": {
                "max_plan_audit_chars": max_chars,
                "max_plan_audit_output_words": 250,
                "max_context_chars": 9000,
            },
            "next_action": {"mode": "audit_experiment_plan", "queue_id": "Q-001"},
        },
    )
    return active


def _accept(root: Path, verdict: str = "pass", extra: str = "") -> dict:
    bundle = build_plan_review_bundle(root, EXPERIMENT_ID)
    (bundle / "PLAN_AUDIT.md").write_text(
        _audit(verdict, extra), encoding="utf-8"
    )
    accept_plan_audit(root, EXPERIMENT_ID)
    return json.loads(
        (root / f"experiments/active/{EXPERIMENT_ID}/MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )


def test_changed_novelty_invalidates_accepted_plan_audit(tmp_path: Path) -> None:
    from test_research_memory import _novelty

    from scripts.research_memory import append_jsonl

    active = _root(tmp_path)
    novelty = _novelty(EXPERIMENT_ID)
    path = tmp_path / "research/novelty/NOVELTY_CHECKS.jsonl"
    append_jsonl(path, novelty)
    manifest = _accept(tmp_path)
    request = json.loads(
        (tmp_path / f"review/bundles/{EXPERIMENT_ID}-plan/PLAN_AUDIT_REQUEST.json").read_text()
    )
    assert request["novelty"] == novelty
    novelty["novelty_claim"] = "a different mechanism"
    append_jsonl(path, novelty)
    with pytest.raises(PlanAuditRequiredError, match="inputs changed"):
        require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=True)


def test_lock_routes_draft_to_plan_audit(tmp_path: Path) -> None:
    active = _root(tmp_path)
    config_path = tmp_path / f"configs/experiments/{EXPERIMENT_ID}.json"
    config = json.loads(
        (REPO_ROOT / "configs/templates/smoke.json").read_text(encoding="utf-8")
    )
    config["experiment"].update(
        {
            "id": EXPERIMENT_ID,
            "queue_id": "Q-001",
            "output_dir": f"artifacts/results/{EXPERIMENT_ID}",
        }
    )
    _write_json(config_path, config)
    _write_json(
        active / "SCOPE.json",
        {
            "schema_version": "1.3",
            "read_paths": [],
            "write_paths": ["src/change.py"],
            "test_paths": [],
            "change_targets": [
                {
                    "path": "src/change.py",
                    "role": "intervention",
                    "action": "modify",
                    "symbols": ["transform"],
                }
            ],
            "planning_reads": [],
            "implementation_entry_reads": [],
        },
    )
    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    state.update(
        {
            "phase": "DRAFT",
            "approvals": {"plan_review_experiment_id": EXPERIMENT_ID},
            "review_policy": {"independent_stages": ["pilot", "full"]},
            "next_action": {"mode": "plan_experiment", "queue_id": "Q-001"},
        }
    )
    state["budgets"].update(
        {
            "max_experiment_plan_words": 700,
            "max_scope_files": 10,
            "max_planning_python_reads": 3,
            "max_implementation_entry_python_reads": 3,
        }
    )
    _write_json(tmp_path / "research/STATE.json", state)
    manifest = {
        "id": EXPERIMENT_ID,
        "phase": "DRAFT",
        "stage": "smoke",
        "queue_id": "Q-001",
        "baseline_id": None,
        "config": f"configs/experiments/{EXPERIMENT_ID}.json",
        "plan_audit": {"verdict": "pass"},
    }
    _write_json(active / "MANIFEST.json", manifest)
    _write_json(
        tmp_path / "experiments/INDEX.json",
        {"experiments": [{"id": EXPERIMENT_ID, "phase": "DRAFT"}]},
    )

    lock_plan(tmp_path, EXPERIMENT_ID)

    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (active / "MANIFEST.json").read_text(encoding="utf-8")
    )
    assert state["phase"] == "PLANNED"
    assert state["next_action"]["mode"] == "audit_experiment_plan"
    assert state["approvals"]["plan_review_experiment_id"] is None
    assert manifest["plan_audit"] is None
    assert manifest["plan_review"] == {"status": "pending"}
    assert manifest["implementation_delta"]["status"] == "locked"
    assert (active / "IMPLEMENTATION_DELTA.json").is_file()


def test_plan_audit_accepts_pass_and_routes_to_human_review(tmp_path: Path) -> None:
    active = _root(tmp_path)
    manifest = _accept(tmp_path)

    require_accepted_plan_audit(
        tmp_path, active, manifest, allow_warn=False
    )
    state = json.loads(
        (tmp_path / "research/STATE.json").read_text(encoding="utf-8")
    )
    assert state["next_action"]["mode"] == "review_experiment_plan"


def test_plan_audit_bundle_stays_within_9000_characters(tmp_path: Path) -> None:
    _root(tmp_path)
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    size = sum(
        len((bundle / name).read_text(encoding="utf-8"))
        for name in ("PLAN_AUDIT_REQUEST.json", "PLAN_AUDIT.md")
    )
    assert size <= 9000
    request = json.loads((bundle / "PLAN_AUDIT_REQUEST.json").read_text(encoding="utf-8"))
    assert "research goal" in request["review_question"]
    assert "Evidence coverage:" in request["locked_plan"]
    assert "Scale justification:" in request["locked_plan"]


def test_plan_bundle_blocks_incomplete_scale_before_auditor(tmp_path: Path) -> None:
    active = _root(tmp_path)
    text = _record().replace(
        "- Scale justification: two batches check execution only; "
        "later comparisons supply research evidence",
        "- Scale justification: pending",
    )
    (active / "EXPERIMENT.md").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Scale justification"):
        build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    assert not (tmp_path / "review/bundles").exists()


@pytest.mark.parametrize("value", [None, "pending"])
def test_plan_audit_requires_scale_assessment(tmp_path: Path, value: str | None) -> None:
    active = _root(tmp_path)
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    text = _audit().replace(
        "- Research scale adequacy: readiness; "
        "core comparisons required before claiming research support",
        "" if value is None else f"- Research scale adequacy: {value}",
    )
    (bundle / "PLAN_AUDIT.md").write_text(text, encoding="utf-8")
    before = (active / "MANIFEST.json").read_bytes()
    with pytest.raises(ValueError, match="Research scale adequacy"):
        accept_plan_audit(tmp_path, EXPERIMENT_ID)
    assert (active / "MANIFEST.json").read_bytes() == before


def test_audit_survives_managed_controls_but_not_scientific_change(
    tmp_path: Path,
) -> None:
    active = _root(tmp_path)
    manifest = _accept(tmp_path)
    config_path = tmp_path / manifest["config"]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["data"]["batch_size"] = 64
    config["train"]["optimizer"]["learning_rate"] = 0.003
    _write_json(config_path, config)
    require_accepted_plan_audit(
        tmp_path, active, manifest, allow_warn=False
    )

    config["evaluation"]["primary_metric"] = "shortcut_accuracy"
    _write_json(config_path, config)
    with pytest.raises(PlanAuditRequiredError, match="inputs changed"):
        require_accepted_plan_audit(
            tmp_path, active, manifest, allow_warn=False
        )


def test_plan_audit_text_is_immutable_after_acceptance(tmp_path: Path) -> None:
    active = _root(tmp_path)
    manifest = _accept(tmp_path)
    (active / "PLAN_AUDIT.md").write_text(
        _audit().replace("nuisance selection", "no risk"),
        encoding="utf-8",
    )
    with pytest.raises(PlanAuditRequiredError, match="changed after acceptance"):
        require_accepted_plan_audit(
            tmp_path, active, manifest, allow_warn=False
        )


def test_plan_audit_rejects_output_over_250_words(tmp_path: Path) -> None:
    _root(tmp_path)
    bundle = build_plan_review_bundle(tmp_path, EXPERIMENT_ID)
    (bundle / "PLAN_AUDIT.md").write_text(
        _audit(extra=" ".join(["detail"] * 260)), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="exceeds 250 words"):
        accept_plan_audit(tmp_path, EXPERIMENT_ID)


def test_plan_audit_rejects_bundle_over_9000_characters(tmp_path: Path) -> None:
    _root(tmp_path)
    (tmp_path / "research/GOAL.md").write_text(
        "# Research Goal\n" + ("x" * 9000), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="exceeds 9000 characters"):
        build_plan_review_bundle(tmp_path, EXPERIMENT_ID)


def test_warn_never_satisfies_unattended_plan_gate(tmp_path: Path) -> None:
    active = _root(tmp_path)
    manifest = _accept(tmp_path, verdict="warn")
    require_accepted_plan_audit(tmp_path, active, manifest, allow_warn=True)
    with pytest.raises(PlanAuditRequiredError, match="verdict pass"):
        require_accepted_plan_audit(
            tmp_path, active, manifest, allow_warn=False
        )


def test_fail_never_satisfies_human_plan_gate(tmp_path: Path) -> None:
    active = _root(tmp_path)
    manifest = _accept(tmp_path, verdict="fail")
    with pytest.raises(PlanAuditRequiredError, match="pass or warn"):
        require_accepted_plan_audit(
            tmp_path, active, manifest, allow_warn=True
        )
