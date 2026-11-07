from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.complete_direction_update import complete_direction_update
from scripts.complete_memory_update import complete_memory_update
from scripts.new_experiment import create_experiment
from scripts.next_autonomous_step import next_autonomous_step


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_root(root: Path) -> None:
    (root / "research").mkdir(parents=True, exist_ok=True)
    (root / "research/GOAL.md").write_text("# Research Goal\n", encoding="utf-8")
    (root / "experiments").mkdir(parents=True, exist_ok=True)
    (root / "experiments/DIGEST.md").write_text("# Digest\n", encoding="utf-8")
    _write_json(
        root / "research/STATE.json",
        {
            "project_id": "test",
            "project_status": "ready",
            "active_experiment": None,
            "phase": None,
            "stage": None,
            "review_required": False,
            "latest_completed_experiment": "EXP-TEST",
            "active_evidence_ids": [],
            "active_claim_ids": ["C-001"],
            "budgets": {"max_context_chars": 9000},
            "next_action": {"mode": "maintain_memory", "queue_id": "Q-001"},
        },
    )
    (root / "experiments/LEDGER.jsonl").write_text(
        '{"experiment_id":"EXP-TEST"}\n', encoding="utf-8"
    )
    (root / "research/EVIDENCE.jsonl").write_text(
        '{"id":"E-EXP-TEST","experiment_id":"EXP-TEST","claim_ids":["C-001"],'
        '"decision":"support","decision_rule_assessment":"expected trend observed",'
        '"primary_result":"improved",'
        '"supported_scope":"test scope",'
        '"unsupported_or_missing_evidence":"other scopes",'
        '"integrity_verdict":"pass",'
        '"record":"experiments/completed/EXP-TEST/EXPERIMENT.md",'
        '"metrics":"artifacts/results/EXP-TEST/metrics.json"}\n',
        encoding="utf-8",
    )
    completed = root / "experiments/completed/EXP-TEST"
    completed.mkdir(parents=True)
    (completed / "EXPERIMENT.md").write_text(
        "- Decision: support\n"
        "- Mechanical rule status: trend_requires_interpretation\n"
        "- Decision-rule assessment: expected trend observed\n"
        "- Primary result: improved\n"
        "- Supported scope: test scope\n"
        "- Unsupported or missing evidence: other scopes\n",
        encoding="utf-8",
    )
    _write_json(completed / "MANIFEST.json", {"integrity_audit": {"verdict": "pass"}})


def test_memory_then_direction_advances_to_selection(tmp_path: Path) -> None:
    _base_root(tmp_path)
    complete_memory_update(tmp_path)
    state = json.loads((tmp_path / "research/STATE.json").read_text(encoding="utf-8"))
    assert state["next_action"]["mode"] == "update_direction"
    assert state["active_evidence_ids"] == ["E-EXP-TEST"]

    complete_direction_update(tmp_path)
    state = json.loads((tmp_path / "research/STATE.json").read_text(encoding="utf-8"))
    assert state["next_action"]["mode"] == "select_experiment"


@pytest.mark.parametrize("mode", ["initial_setup", "update_direction", "select_experiment"])
def test_memory_completion_cannot_rewind_other_operations(tmp_path: Path, mode: str) -> None:
    _base_root(tmp_path)
    path = tmp_path / "research/STATE.json"
    state = json.loads(path.read_text())
    state["next_action"]["mode"] = mode
    _write_json(path, state)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="next action is not maintain_memory"):
        complete_memory_update(tmp_path)
    assert path.read_bytes() == before
    assert not (tmp_path / "research/CONTEXT.md").exists()


@pytest.mark.parametrize("mode", ["initial_setup", "maintain_memory", "update_direction"])
def test_creation_cannot_skip_required_operations(tmp_path: Path, mode: str) -> None:
    _base_root(tmp_path)
    active = tmp_path / "experiments/active"
    active.mkdir()
    path = tmp_path / "research/STATE.json"
    state = json.loads(path.read_text())
    state["next_action"]["mode"] = mode
    _write_json(path, state)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="next action is not select_experiment"):
        create_experiment(tmp_path, experiment_id="EXP-NEXT", stage="smoke")
    assert path.read_bytes() == before
    assert list(active.iterdir()) == []
    assert not (tmp_path / "configs").exists()


def test_post_result_handoff_creates_exactly_one_draft(tmp_path: Path) -> None:
    _base_root(tmp_path)
    (tmp_path / "experiments/active").mkdir()
    _write_json(tmp_path / "experiments/INDEX.json", {"experiments": []})
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "configs/templates/smoke.json",
        "experiments/templates/EXPERIMENT.md",
        "experiments/templates/SCOPE.json",
        "experiments/templates/MANIFEST.json",
        "experiments/templates/EXPERIMENT_AGENTS.md",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    complete_memory_update(tmp_path)
    complete_direction_update(tmp_path)
    assert "skill=$select-next-experiment" in next_autonomous_step(tmp_path)
    draft = create_experiment(tmp_path, experiment_id="EXP-NEXT", stage="smoke")
    state_path = tmp_path / "research/STATE.json"
    state = json.loads(state_path.read_text())
    assert state["next_action"]["mode"] == "plan_experiment"
    assert state["active_experiment"] == "EXP-NEXT"
    assert json.loads((draft / "MANIFEST.json").read_text())["phase"] == "DRAFT"
    before = state_path.read_bytes()
    with pytest.raises(RuntimeError, match="active experiment already exists"):
        create_experiment(tmp_path, experiment_id="EXP-SECOND", stage="smoke")
    assert state_path.read_bytes() == before
    assert not (tmp_path / "experiments/active/EXP-SECOND").exists()
