from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_decision_facts import EXPERIMENT_ID, _root
from test_plan_audit import _record

from scripts.build_context import build_context
from scripts.build_decision_facts import (
    DecisionFactsRequiredError,
    build_decision_facts,
    require_current_decision_facts,
)
from scripts.common import atomic_write_json
from scripts.records import research_focus


@pytest.mark.parametrize("active", [True, False])
def test_context_preserves_focus_during_and_after_experiment(tmp_path: Path, active: bool) -> None:
    question = "\n".join(f"Question condition {i}." for i in range(20))
    goal = f"# Research Goal\n## Question\n{question}\n## Decision\nAdopt or reject.\n"
    record = _record()
    area = "active" if active else "completed"
    path = tmp_path / "experiments" / area / EXPERIMENT_ID / "EXPERIMENT.md"
    path.parent.mkdir(parents=True)
    path.write_text(record)
    atomic_write_json(tmp_path / "research/STATE.json", {
        "active_experiment": EXPERIMENT_ID if active else None,
        "latest_completed_experiment": None if active else EXPERIMENT_ID,
        "budgets": {"max_context_chars": 2500},
    })
    (tmp_path / "research/GOAL.md").write_text(goal)
    (tmp_path / "research/memory").mkdir()
    (tmp_path / "research/memory/INSIGHTS.md").write_text("- " + "large memory " * 1000)
    (tmp_path / "experiments/DIGEST.md").write_text("large digest " * 1000)
    text = build_context(tmp_path).read_text()
    assert len(text) <= 2500
    assert text.index("## Research Focus") < text.index("## State")
    for value in research_focus(goal, record).values():
        assert " ".join(value.split()) in text
    assert f"experiments/{area}/{EXPERIMENT_ID}/EXPERIMENT.md" in text
    assert "not a proven result" in text


def test_tiny_budget_fails_without_silently_losing_question(tmp_path: Path) -> None:
    atomic_write_json(tmp_path / "research/STATE.json", {"budgets": {"max_context_chars": 100}})
    (tmp_path / "research/GOAL.md").write_text("## Question\nWhat does the method explain?\n")
    with pytest.raises(ValueError, match="cannot preserve Research Focus"):
        build_context(tmp_path)
    assert not (tmp_path / "research/CONTEXT.md").exists()


@pytest.mark.parametrize("changed", ["question", "novelty"])
def test_decision_facts_bind_question_and_novelty_but_not_conclusion(
    tmp_path: Path, changed: str,
) -> None:
    active = _root(tmp_path)
    goal = tmp_path / "research/GOAL.md"
    goal.write_text("## Question\nDoes adaptation explain the shift response?\n")
    record = active / "EXPERIMENT.md"
    record.write_text(_record())
    facts = json.loads(build_decision_facts(tmp_path, EXPERIMENT_ID).read_text())
    manifest = json.loads((active / "MANIFEST.json").read_text())
    assert facts["research_focus"] == research_focus(goal.read_text(), record.read_text())
    record.write_text(record.read_text().replace("- Decision: pending", "- Decision: inconclusive"))
    require_current_decision_facts(tmp_path, active, manifest)
    if changed == "question":
        goal.write_text("## Question\nDoes a different method explain another task?\n")
    else:
        record.write_text(record.read_text().replace("tests a distinct mechanism", "a new claim"))
    with pytest.raises(DecisionFactsRequiredError, match="inputs changed"):
        require_current_decision_facts(tmp_path, active, manifest)
