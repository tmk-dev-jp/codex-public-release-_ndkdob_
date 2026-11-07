from __future__ import annotations

import json
from pathlib import Path

import pytest

from dl_research.config import load_config
from dl_research.exceptions import PolicyError
from dl_research.experiment.policy import enforce_execution_policy
from scripts import validate as repository_validation


def _state(root: Path) -> None:
    path = root / "research/STATE.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "execution_policy": {
                    "smoke": {
                        "max_epochs": 1,
                        "max_train_batches": 2,
                        "max_validation_batches": 2,
                        "max_test_batches": 2,
                    },
                    "pilot": {
                        "max_epochs": 5,
                        "max_train_batches": 20,
                        "max_validation_batches": 10,
                        "max_test_batches": 10,
                    },
                    "full": {"requires_explicit_approval": True},
                },
                "approvals": {"full_training_experiment_id": None},
            }
        ),
        encoding="utf-8",
    )


def test_smoke_policy_accepts_bounded_config(tmp_path: Path) -> None:
    _state(tmp_path)
    config = load_config(Path("configs/templates/smoke.json"))
    enforce_execution_policy(config, tmp_path)


def test_full_policy_requires_matching_approval(tmp_path: Path) -> None:
    _state(tmp_path)
    config = load_config(Path("configs/templates/full.json"))
    with pytest.raises(PolicyError):
        enforce_execution_policy(config, tmp_path)


def test_research_code_policy_orders_minimality_choices() -> None:
    root = Path(__file__).resolve().parents[2]
    policy = (
        root
        / ".agents/skills/implement-experiment/references/RESEARCH_CODE_POLICY.md"
    ).read_text(encoding="utf-8")
    choices = (
        "Avoid code",
        "Reuse an existing",
        "Use the standard library",
        "Use an already-installed dependency",
        "Write the minimum new code",
    )

    positions = [policy.index(choice) for choice in choices]
    assert positions == sorted(positions)
    assert "request plan revision before crossing scope" in policy
    assert "data-loss prevention" in policy


def test_implementation_skill_applies_the_minimality_ladder() -> None:
    root = Path(__file__).resolve().parents[2]
    skill = (root / ".agents/skills/implement-experiment/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "apply the minimality ladder" in skill
    assert "fix the shared root cause" in skill
    assert "preserve all locked scientific controls" in skill


def test_model_profiles_are_explicit_and_token_bounded() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = {
        "research-planner.toml": ("gpt-6-astra", "high"),
        "plan-auditor.toml": ("gpt-6-astra", "high"),
        "mechanical-implementer.toml": ("gpt-5.6-luna", "medium"),
        "experiment-implementer.toml": ("gpt-5.6-terra", "medium"),
        "scientific-implementer.toml": ("gpt-6-astra", "high"),
    }
    for filename, (model, effort) in expected.items():
        text = (root / ".codex/agents" / filename).read_text(encoding="utf-8")
        assert f'model = "{model}"' in text
        assert f'model_reasoning_effort = "{effort}"' in text
    config = (root / ".codex/config.toml").read_text(encoding="utf-8")
    for key in ("max_concurrent_threads_per_session", "max_threads", "max_depth"):
        assert f"{key} =" not in config


def test_plan_audit_prohibits_metric_packing_and_reviewer_panels() -> None:
    root = Path(__file__).resolve().parents[2]
    skill = (root / ".agents/skills/audit-experiment-plan/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "at most one diagnostic guardrail" in skill
    assert "must never become a second promotion metric" in skill
    assert "Do not create a reviewer panel" in skill
    assert "9,000 characters" in skill
    assert "250 words" in skill


def test_direction_update_preserves_goal_coverage_before_minimizing_cost() -> None:
    root = Path(__file__).resolve().parents[2]
    skill = (
        root / ".agents/skills/update-research-direction/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Limit claims to observed evidence" in skill
    assert "do not abandon necessary study coverage just to avoid cost" in skill
    assert "Queue at most one adequate next experiment" in skill
    assert "Research-goal changes need human agreement" in skill
    assert "not post-hoc metrics/patterns" in skill


def test_independent_judgment_is_in_effective_role_instructions() -> None:
    root = Path(__file__).resolve().parents[2]
    for filename in repository_validation.MODEL_AGENT_POLICIES:
        text = (root / filename).read_text(encoding="utf-8")
        instructions = " ".join(
            text.split('developer_instructions = """', 1)[1].split('"""', 1)[0].split()
        )
        for marker in repository_validation.INDEPENDENT_JUDGMENT_MARKERS:
            assert marker in instructions, filename
        assert "role's scope, source and output limits" in instructions


def test_validation_detects_removed_independent_judgment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[2]
    targets = (
        *repository_validation.MODEL_AGENT_POLICIES,
        ".agents/skills/run-one-agent-led-loop/references/DECISIONS.md",
    )
    original_read = repository_validation._read_text

    def without_policy(path: Path) -> str:
        text = original_read(path)
        if path.relative_to(root).as_posix() in targets:
            text = " ".join(text.split())
            for marker in repository_validation.INDEPENDENT_JUDGMENT_MARKERS:
                text = text.replace(marker, "")
        return text

    monkeypatch.setattr(repository_validation, "_read_text", without_policy)
    errors, _ = repository_validation.validate(root)
    for filename in targets:
        for marker in repository_validation.INDEPENDENT_JUDGMENT_MARKERS:
            assert f"independent judgment policy missing {marker}: {filename}" in errors
