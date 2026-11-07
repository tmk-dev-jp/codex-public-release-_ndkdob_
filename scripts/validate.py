from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
SRC = _REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dl_research.config import load_config
from scripts.common import QuietArgumentParser, one_line, read_json, root_from_script
from scripts.records import validate_experiment_headings, validate_record_word_limits
from scripts.research_memory import (
    LEDGER_KEYS,
    validate_evidence,
    validate_idea_bank,
    validate_jsonl_schema,
    validate_novelty_checks,
)
from scripts.scope import validate_scope

JAPANESE = re.compile(r"[ぁ-んァ-ン一-龯々]")
REQUIRED_HEADINGS = [
    "## Hypothesis",
    "## Method",
    "## Conclusion",
    "## Issues and Next Direction",
]
REQUIRED_DIRECTORIES = [
    ".codex/agents",
    ".codex/hooks",
    ".agents/skills/plan-experiment",
    ".agents/skills/implement-experiment",
    ".agents/skills/review-experiment-plan",
    ".agents/skills/approve-or-revise-plan",
    ".agents/skills/revise-experiment-plan",
    ".agents/skills/review-experiment-result",
    ".agents/skills/request-human-result-interpretation",
    ".agents/skills/update-research-direction",
    ".agents/skills/select-next-experiment",
    ".agents/skills/evaluate-experiment",
    ".agents/skills/debug-failure",
    ".agents/skills/initial-setup",
    ".agents/skills/migrate-research-project",
    ".agents/skills/compress-audit-material",
    ".agents/skills/checkpoint-reproducibility",
    ".agents/skills/set-subagent-defaults",
    ".agents/skills/configure-hypothesis-policy",
    ".agents/skills/scan-research-landscape",
    ".agents/skills/replenish-research-hypotheses",
    ".agents/skills/audit-novelty",
    ".agents/skills/select-research-branch",
    ".agents/skills/maintain-research-memory",
    ".agents/skills/monitor-experiment",
    ".agents/skills/run-autonomous-loop",
    ".agents/skills/run-one-unattended-loop",
    ".agents/skills/run-one-agent-led-loop",
    ".agents/skills/run-experiment",
    ".agents/skills/audit-experiment-plan",
    ".agents/skills/audit-experiment-implementation",
    ".agents/skills/audit-experiment-integrity",
    ".agents/skills/review-research-loop",
    ".agents/skills/apply-research-loop-improvement",
    "automation",
    "baselines/records",
    "baselines/templates",
    "configs/templates",
    "configs/experiments",
    "src/dl_research/data",
    "src/dl_research/models",
    "src/dl_research/training",
    "src/dl_research/evaluation",
    "src/dl_research/experiment",
    "src/dl_research/cli",
    "research/planning",
    "research/memory",
    "research/ideas",
    "research/novelty",
    "experiments/templates",
    "experiments/active",
    "experiments/completed",
    "data/raw",
    "data/processed",
    "artifacts/results",
    "references/inbox",
    "references/originals",
    "references/records",
    "review/bundles",
    "review/completed",
    "scripts",
    "schemas",
    "tests/unit",
    "tests/smoke",
    "human",
    "human/templates",
]
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "human/README.ja.md",
    "human/QUICKSTART.ja.md",
    "human/MANUAL.ja.md",
    "human/MIGRATE_RESEARCH.ja.md",
    "human/TREE.ja.txt",
    "human/templates/HUMAN_RESULTS.md",
    "human/templates/HUMAN_INTERPRETATION.md",
    "TREE.txt",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".agents/skills/audit-experiment-implementation/agents/openai.yaml",
    ".agents/skills/audit-experiment-plan/agents/openai.yaml",
    ".codex/agents/evaluator.toml",
    ".codex/agents/research-planner.toml",
    ".codex/agents/plan-auditor.toml",
    ".codex/agents/mechanical-implementer.toml",
    ".codex/agents/experiment-implementer.toml",
    ".codex/agents/scientific-implementer.toml",
    ".agents/skills/run-one-unattended-loop/agents/openai.yaml",
    ".agents/skills/migrate-research-project/references/MIGRATION.md",
    "scripts/migration_source.py",
    "scripts/compress_audit_material.py",
    "scripts/reproducibility_checkpoint.py",
    "scripts/update_template.py",
    "human/REPRODUCIBILITY.ja.md",
    "human/UPDATE_TEMPLATE.ja.md",
    "automation/ONE_CYCLE_PROMPT.md",
    "automation/AUTONOMOUS_LOOP_PROMPT.md",
    "automation/UNATTENDED_LOOP_PROMPT.md",
    "human/AUTONOMOUS_LOOP.ja.md",
    "human/UNATTENDED_LOOP.ja.md",
    "baselines/INDEX.json",
    "baselines/templates/BASELINE.json",
    "research/GOAL.md",
    "research/PROPOSED_METHOD.md",
    "research/TRAINING_CONTROLS.json",
    "research/STATE.json",
    "research/QUEUE.json",
    "research/planning/HYPOTHESIS_POLICY.md",
    "research/memory/INSIGHTS.md",
    "research/memory/DEAD_ENDS.md",
    "research/memory/OPEN_QUESTIONS.md",
    "research/ideas/IDEA_BANK.jsonl",
    "research/novelty/NOVELTY_CHECKS.jsonl",
    "research/CONTEXT.md",
    "experiments/LEDGER.jsonl",
    "experiments/templates/EXPERIMENT.md",
    "experiments/templates/EVALUATION.md",
    "experiments/templates/SCOPE.json",
    "experiments/templates/MANIFEST.json",
    "references/templates/REFERENCE.md",
    "references/SETUP_MANUAL.md",
    "data/MANIFEST.example.json",
    "scripts/approve_full.py",
    "scripts/approve_plan.py",
    "scripts/return_plan_to_draft.py",
    "scripts/build_human_result_packet.py",
    "scripts/accept_human_interpretation.py",
    "scripts/tune_training_controls.py",
    "scripts/research_memory.py",
    "scripts/monitor_experiment.py",
    "scripts/next_autonomous_step.py",
    "scripts/next_unattended_loop_step.py",
    "scripts/next_agent_led_loop_step.py",
    "scripts/research_decision.py",
    ".agents/skills/run-one-agent-led-loop/references/DECISIONS.md",
    ".agents/skills/run-one-agent-led-loop/agents/openai.yaml",
    "human/AGENT_LED_LOOP.ja.md",
    "automation/AGENT_LED_LOOP_PROMPT.md",
    "automation/INDEPENDENT_JUDGMENT.md",
    "human/INDEPENDENT_JUDGMENT.ja.md",
    "scripts/next_agent_action.py",
    "scripts/build_decision_facts.py",
    "scripts/implementation_delta.py",
    "scripts/suggest_novelty_axes.py",
    "scripts/register_baseline.py",
    "scripts/build_implementation_review_bundle.py",
    "scripts/build_plan_review_bundle.py",
    "scripts/accept_plan_audit.py",
    "scripts/accept_implementation_audit.py",
    "scripts/accept_integrity_audit.py",
    "scripts/complete_memory_update.py",
    "scripts/complete_direction_update.py",
    "experiments/templates/IMPLEMENTATION_AUDIT.md",
    "experiments/templates/PLAN_AUDIT.md",
    "experiments/templates/INTEGRITY_AUDIT.md",
]
REQUIRED_AGENT_FILES = [
    "AGENTS.md",
    "automation/AGENTS.md",
    "baselines/AGENTS.md",
    "configs/AGENTS.md",
    "data/AGENTS.md",
    "experiments/AGENTS.md",
    "research/AGENTS.md",
    "research/planning/AGENTS.md",
    "research/memory/AGENTS.md",
    "research/ideas/AGENTS.md",
    "research/novelty/AGENTS.md",
    "src/AGENTS.md",
    "scripts/AGENTS.md",
    "artifacts/AGENTS.md",
    "references/AGENTS.md",
    "review/bundles/AGENTS.md",
]
AGENT_CHAINS = [
    ["AGENTS.md", "automation/AGENTS.md"],
    ["AGENTS.md", "baselines/AGENTS.md"],
    ["AGENTS.md", "configs/AGENTS.md"],
    ["AGENTS.md", "data/AGENTS.md"],
    ["AGENTS.md", "experiments/AGENTS.md"],
    ["AGENTS.md", "research/AGENTS.md", "research/planning/AGENTS.md"],
    ["AGENTS.md", "research/AGENTS.md", "research/memory/AGENTS.md"],
    ["AGENTS.md", "research/AGENTS.md", "research/ideas/AGENTS.md"],
    ["AGENTS.md", "research/AGENTS.md", "research/novelty/AGENTS.md"],
    ["AGENTS.md", "src/AGENTS.md"],
    ["AGENTS.md", "scripts/AGENTS.md"],
    ["AGENTS.md", "artifacts/AGENTS.md"],
    ["AGENTS.md", "references/AGENTS.md"],
    ["AGENTS.md", "review/bundles/AGENTS.md"],
]
SKILL_FILES = [
    ".agents/skills/set-subagent-defaults/SKILL.md",
    ".agents/skills/checkpoint-reproducibility/SKILL.md",
    ".agents/skills/initial-setup/SKILL.md",
    ".agents/skills/migrate-research-project/SKILL.md",
    ".agents/skills/compress-audit-material/SKILL.md",
    ".agents/skills/configure-hypothesis-policy/SKILL.md",
    ".agents/skills/scan-research-landscape/SKILL.md",
    ".agents/skills/replenish-research-hypotheses/SKILL.md",
    ".agents/skills/audit-novelty/SKILL.md",
    ".agents/skills/select-research-branch/SKILL.md",
    ".agents/skills/maintain-research-memory/SKILL.md",
    ".agents/skills/monitor-experiment/SKILL.md",
    ".agents/skills/run-autonomous-loop/SKILL.md",
    ".agents/skills/run-one-unattended-loop/SKILL.md",
    ".agents/skills/run-one-agent-led-loop/SKILL.md",
    ".agents/skills/run-experiment/SKILL.md",
    ".agents/skills/audit-experiment-plan/SKILL.md",
    ".agents/skills/audit-experiment-implementation/SKILL.md",
    ".agents/skills/audit-experiment-integrity/SKILL.md",
    ".agents/skills/review-research-loop/SKILL.md",
    ".agents/skills/apply-research-loop-improvement/SKILL.md",
    ".agents/skills/query-paper-knowledge/SKILL.md",
    ".agents/skills/research-paper-graph/SKILL.md",
    ".agents/skills/prepare-environment/SKILL.md",
    ".agents/skills/prepare-data-manifest/SKILL.md",
    ".agents/skills/define-research-intent/SKILL.md",
    ".agents/skills/register-source-baseline/SKILL.md",
    ".agents/skills/plan-experiment/SKILL.md",
    ".agents/skills/review-experiment-plan/SKILL.md",
    ".agents/skills/approve-or-revise-plan/SKILL.md",
    ".agents/skills/revise-experiment-plan/SKILL.md",
    ".agents/skills/discuss-implementation-design/SKILL.md",
    ".agents/skills/review-experiment-result/SKILL.md",
    ".agents/skills/request-human-result-interpretation/SKILL.md",
    ".agents/skills/update-research-direction/SKILL.md",
    ".agents/skills/select-next-experiment/SKILL.md",
    ".agents/skills/implement-experiment/SKILL.md",
    ".agents/skills/evaluate-experiment/SKILL.md",
    ".agents/skills/debug-failure/SKILL.md",
]
ALLOWED_PRINT = {
    Path("src/dl_research/cli/common.py"),
    Path("scripts/common.py"),
    Path("scripts/run_experiment.py"),
    Path("scripts/migration_source.py"),
    Path("scripts/validate.py"),
    Path(".codex/hooks/stop_validate.py"),
}
ALLOWED_BROAD_EXCEPT = ALLOWED_PRINT
PROHIBITED_CODE_MARKERS = {
    "tqdm": "progress dependency",
    "import logging": "logging dependency",
    "logging.": "logging dependency",
    "import traceback": "traceback dependency",
    "traceback.": "traceback dependency",
    "breakpoint(": "debug breakpoint",
    "import pdb": "debugger dependency",
    "pdb.": "debugger dependency",
    "tenacity": "automatic retry dependency",
    "retrying": "automatic retry dependency",
}
MODEL_AGENT_POLICIES = {
    ".codex/agents/evaluator.toml": (
        'sandbox_mode = "read-only"',
        "`DECISION_FACTS.json` as authoritative",
        "Do not redo hash, file-presence, arithmetic, or schema checks.",
    ),
    ".codex/agents/research-planner.toml": (
        'model = "gpt-6-astra"',
        'model_reasoning_effort = "high"',
    ),
    ".codex/agents/plan-auditor.toml": (
        'model = "gpt-6-astra"',
        'model_reasoning_effort = "high"',
        'sandbox_mode = "read-only"',
    ),
    ".codex/agents/mechanical-implementer.toml": (
        'model = "gpt-5.6-luna"',
        'model_reasoning_effort = "medium"',
    ),
    ".codex/agents/experiment-implementer.toml": (
        'model = "gpt-5.6-terra"',
        'model_reasoning_effort = "medium"',
    ),
    ".codex/agents/scientific-implementer.toml": (
        'model = "gpt-6-astra"',
        'model_reasoning_effort = "high"',
    ),
}
INDEPENDENT_JUDGMENT_MARKERS = (
    "User preference, supervisor confidence and peer agreement are not evidence.",
    "Do not manufacture disagreement.",
    "new evidence or an identified reasoning error",
)
AGENT_GATE_SKILLS = {
    ".agents/skills/debug-failure/SKILL.md": "--task repair",
    ".agents/skills/plan-experiment/SKILL.md": "--task planning",
    ".agents/skills/implement-experiment/SKILL.md": "--task implementation",
    ".agents/skills/audit-experiment-plan/SKILL.md": "--task plan-audit",
    ".agents/skills/audit-experiment-implementation/SKILL.md": (
        "--task implementation-audit"
    ),
    ".agents/skills/audit-experiment-integrity/SKILL.md": "--task integrity-audit",
    ".agents/skills/evaluate-experiment/SKILL.md": "--task evaluation",
}
REQUIRED_TEXT_MARKERS = {
    "AGENTS.md": "automation/INDEPENDENT_JUDGMENT.md",
    "automation/INDEPENDENT_JUDGMENT.md": "Preserve the worker's output and unresolved objections.",
    "experiments/templates/EXPERIMENT.md": "Mechanical rule status",
    "experiments/templates/EVALUATION.md": "Mechanical rule status",
    "human/templates/HUMAN_INTERPRETATION.md": "Mechanical rule status",
    "experiments/templates/MANIFEST.json": '"implementation_delta"',
    ".agents/skills/request-human-result-interpretation/SKILL.md": (
        "Copy `Mechanical rule status` exactly"
    ),
}


def _json_files(root: Path):
    for path in root.rglob("*.json"):
        if ".git" not in path.parts:
            yield path


def _relative_file(root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must be repository-relative")
    return root / candidate


def _validate_baselines(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "baselines/INDEX.json"
    if not index_path.is_file():
        return errors
    index = read_json(index_path)
    seen: set[str] = set()
    for item in index.get("baselines", []):
        baseline_id = item.get("id")
        if not isinstance(baseline_id, str) or not re.fullmatch(
            r"BASE-[A-Z0-9][A-Z0-9-]*",
            baseline_id,
        ):
            errors.append("invalid baseline ID in baselines/INDEX.json")
            continue
        if baseline_id in seen:
            errors.append(f"duplicate baseline ID: {baseline_id}")
        seen.add(baseline_id)
        record_value = item.get("record")
        if not isinstance(record_value, str):
            errors.append(f"baseline record path missing: {baseline_id}")
            continue
        try:
            record_path = _relative_file(root, record_value)
        except ValueError:
            errors.append(f"invalid baseline record path: {baseline_id}:{record_value}")
            continue
        if not record_path.is_file():
            errors.append(f"baseline record not found: {record_value}")
            continue
        record = read_json(record_path)
        if record.get("id") != baseline_id:
            errors.append(f"baseline index and record ID differ: {baseline_id}")
        source = record.get("source", {})
        if source.get("type") not in {"paper", "github", "web"}:
            errors.append(f"invalid baseline source type: {baseline_id}")
        scope = source.get("approved_reading_scope")
        if not isinstance(scope, list) or not scope:
            errors.append(f"baseline reading scope missing: {baseline_id}")
        implementation = record.get("implementation", {})
        if implementation.get("integration_target") != "src":
            errors.append(f"baseline integration target must be src: {baseline_id}")
        for value in implementation.get("planned_paths", []):
            try:
                relative = _relative_file(root, str(value)).relative_to(root)
            except ValueError:
                errors.append(f"invalid baseline implementation path: {baseline_id}:{value}")
                continue
            if "src" not in relative.parts:
                errors.append(f"baseline implementation path outside src: {baseline_id}:{value}")
    return errors


def _has_broad_except(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            return True
        if isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            return True
        if isinstance(node.type, ast.Tuple):
            for item in node.type.elts:
                if isinstance(item, ast.Name) and item.id in {"Exception", "BaseException"}:
                    return True
    return False


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    state = read_json(root / "research/STATE.json")
    budgets = state.get("budgets", {})
    max_agent = int(budgets.get("max_agent_file_chars", 1400))
    max_chain = int(budgets.get("max_agent_chain_chars", 3200))
    max_skill = int(budgets.get("max_skill_chars", 2200))

    if state.get("code_policy", {}).get("mode") != "research_minimal":
        errors.append("STATE.code_policy.mode must be research_minimal")
    if state.get("code_policy", {}).get("automatic_retries") != 0:
        errors.append("automatic retries must remain disabled")
    if state.get("code_policy", {}).get("progress_output") is not False:
        errors.append("progress output must remain disabled")
    required_budgets = {
        "max_plan_audit_chars": 9000,
        "max_plan_audit_output_words": 250,
        "max_phase_subagents": 1,
        "max_model_escalations": 1,
    }
    for key, expected in required_budgets.items():
        if budgets.get(key) != expected:
            errors.append(f"STATE.budgets.{key} must be {expected}")

    loop_keys = ["unattended_loop"]
    if "agent_led_loop" in state:
        loop_keys.append("agent_led_loop")
    for key in loop_keys:
        control = state.get(key)
        if not isinstance(control, dict):
            errors.append(f"STATE.{key} must be an object")
            continue
        status = control.get("status")
        target = control.get("target_experiment")
        mode = control.get("last_mode")
        if status not in {"idle", "in_progress"}:
            errors.append(f"STATE.{key}.status must be idle or in_progress")
        if status == "idle" and target is not None:
            errors.append(f"idle {key} must not retain a target")
        if status == "in_progress" and (not isinstance(target, str) or not target.strip()):
            errors.append(f"in-progress {key} requires a target")
        if mode is not None and (not isinstance(mode, str) or not mode.strip()):
            errors.append(f"STATE.{key}.last_mode must be null or a non-empty string")
        if status == "in_progress" and mode is None:
            errors.append(f"in-progress {key} requires a last mode")

    if (root / "logs").exists():
        errors.append("logs/ is prohibited")
    for path in root.rglob("*.log"):
        errors.append(f"log file is prohibited: {path.relative_to(root)}")

    for directory in REQUIRED_DIRECTORIES:
        if not (root / directory).is_dir():
            errors.append(f"missing directory: {directory}")
    for filename in REQUIRED_FILES:
        if not (root / filename).is_file():
            errors.append(f"missing file: {filename}")
    for filename in REQUIRED_AGENT_FILES:
        path = root / filename
        if not path.is_file():
            errors.append(f"missing scoped AGENTS.md: {filename}")

    unattended_policy = (
        root / ".agents/skills/run-one-unattended-loop/agents/openai.yaml"
    )
    if unattended_policy.is_file() and (
        "policy:\n  allow_implicit_invocation: false\n"
        not in _read_text(unattended_policy)
    ):
        errors.append("run-one-unattended-loop must disable implicit invocation")

    for filename, required in MODEL_AGENT_POLICIES.items():
        path = root / filename
        if not path.is_file():
            continue
        text = _read_text(path)
        for marker in required:
            if marker not in text:
                errors.append(f"agent policy missing {marker}: {filename}")
    for filename in (
        *MODEL_AGENT_POLICIES,
        ".agents/skills/run-one-agent-led-loop/references/DECISIONS.md",
    ):
        path = root / filename
        if not path.is_file():
            continue  # Missing files are reported by REQUIRED_FILES.
        text = " ".join(_read_text(path).split())
        for marker in INDEPENDENT_JUDGMENT_MARKERS:
            if marker not in text:
                errors.append(f"independent judgment policy missing {marker}: {filename}")
    for filename, task_marker in AGENT_GATE_SKILLS.items():
        path = root / filename
        if path.is_file() and (
            "scripts/next_agent_action.py" not in _read_text(path)
            or task_marker not in _read_text(path)
        ):
            errors.append(f"skill lacks mechanical agent gate: {filename}")
    for filename, marker in REQUIRED_TEXT_MARKERS.items():
        path = root / filename
        if path.is_file() and marker not in _read_text(path):
            errors.append(f"required text marker missing in {filename}: {marker}")

    for filename in SKILL_FILES:
        path = root / filename
        if not path.is_file():
            errors.append(f"missing skill: {filename}")
        elif len(_read_text(path)) > max_skill:
            errors.append(f"skill exceeds {max_skill} chars: {filename}")

    for agents in root.rglob("AGENTS.md"):
        size = len(_read_text(agents))
        if size > max_agent:
            errors.append(
                f"AGENTS.md exceeds {max_agent} chars: {agents.relative_to(root)}"
            )
    for chain in AGENT_CHAINS:
        existing = [root / item for item in chain if (root / item).is_file()]
        size = sum(len(_read_text(path)) for path in existing)
        if size > max_chain:
            errors.append(f"AGENTS.md chain exceeds {max_chain} chars: {' -> '.join(chain)}")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "human" in path.parts:
            continue
        if (
            path.suffix.lower() not in {".md", ".txt", ".py", ".json", ".toml"}
            and path.name != "Makefile"
        ):
            continue
        try:
            text = _read_text(path)
        except UnicodeDecodeError:
            continue
        if path.relative_to(root) != Path("scripts/validate.py") and JAPANESE.search(text):
            errors.append(f"Japanese text outside human/: {path.relative_to(root)}")

    for path in root.rglob("*.py"):
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root)
        text = _read_text(path)
        for marker, label in PROHIBITED_CODE_MARKERS.items():
            if marker in text and relative != Path("scripts/validate.py"):
                errors.append(f"{label} found: {relative}")
        if "print(" in text and relative not in ALLOWED_PRINT:
            errors.append(f"print is restricted to output adapters: {relative}")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python compile error in {relative}: {exc.msg}")
            continue
        if _has_broad_except(tree) and relative not in ALLOWED_BROAD_EXCEPT:
            errors.append(f"broad exception handling outside boundary adapter: {relative}")

    for path in _json_files(root):
        try:
            json.loads(_read_text(path))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON {path.relative_to(root)} line {exc.lineno}")
    errors.extend(_validate_baselines(root))
    errors.extend(validate_idea_bank(root / "research/ideas/IDEA_BANK.jsonl"))
    errors.extend(validate_novelty_checks(root / "research/novelty/NOVELTY_CHECKS.jsonl"))
    errors.extend(
        validate_jsonl_schema(root / "experiments/LEDGER.jsonl", LEDGER_KEYS, "ledger")
    )
    errors.extend(validate_evidence(root / "research/EVIDENCE.jsonl"))

    for path in (root / "configs/templates").glob("*.json"):
        try:
            load_config(path)
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(f"invalid config {path.relative_to(root)}: {exc}")
    for path in (root / "configs/experiments").glob("*.json"):
        try:
            load_config(path)
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(f"invalid config {path.relative_to(root)}: {exc}")

    template = _read_text(root / "experiments/templates/EXPERIMENT.md")
    for heading in REQUIRED_HEADINGS:
        if template.count(heading) != 1:
            errors.append(f"experiment template must contain one {heading}")
    for label in (
        "Baseline behavior",
        "Candidate behavior",
        "Intervention point",
        "Unchanged invariants",
    ):
        if f"- {label}:" not in template:
            errors.append(f"experiment template is missing {label}")

    max_scope_files = int(budgets.get("max_scope_files", 10))
    max_planning_reads = int(budgets.get("max_planning_python_reads", 3))
    max_implementation_entry_reads = int(
        budgets.get("max_implementation_entry_python_reads", 3)
    )
    try:
        validate_scope(
            root,
            read_json(root / "experiments/templates/SCOPE.json"),
            maximum_files=max_scope_files,
            maximum_planning_python_reads=max_planning_reads,
            maximum_implementation_entry_python_reads=max_implementation_entry_reads,
        )
    except (OSError, ValueError) as exc:
        errors.append(f"invalid experiment scope template: {exc}")

    plan_word_limit = int(budgets.get("max_experiment_plan_words", 700))
    conclusion_word_limit = int(
        budgets.get("max_experiment_conclusion_words", 400)
    )
    for status_dir in [
        root / "experiments/active", root / "experiments/completed", root / "experiments/aborted"
    ]:
        if not status_dir.is_dir():
            continue
        for experiment_dir in status_dir.iterdir():
            if not experiment_dir.is_dir() or experiment_dir.name.startswith("."):
                continue
            if not (experiment_dir / "AGENTS.md").is_file():
                errors.append(f"missing experiment AGENTS.md: {experiment_dir.relative_to(root)}")
            record = experiment_dir / "EXPERIMENT.md"
            if not record.is_file():
                errors.append(f"missing experiment record: {experiment_dir.relative_to(root)}")
                continue
            record_text = _read_text(record)
            try:
                validate_experiment_headings(record_text)
            except ValueError as exc:
                errors.append(f"invalid headings {record.relative_to(root)}: {exc}")
            else:
                try:
                    validate_record_word_limits(
                        record_text,
                        maximum_plan_words=plan_word_limit,
                        maximum_conclusion_words=conclusion_word_limit,
                    )
                except ValueError as exc:
                    errors.append(
                        f"invalid record budget {record.relative_to(root)}: {exc}"
                    )
            scope_path = experiment_dir / "SCOPE.json"
            if scope_path.is_file():
                try:
                    validate_scope(
                        root,
                        read_json(scope_path),
                        maximum_files=max_scope_files,
                        maximum_planning_python_reads=max_planning_reads,
                        maximum_implementation_entry_python_reads=(
                            max_implementation_entry_reads
                        ),
                    )
                except (OSError, ValueError) as exc:
                    errors.append(f"invalid scope {scope_path.relative_to(root)}: {exc}")

    active_root = root / "experiments/active"
    active_dirs = [
        path
        for path in active_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ] if active_root.is_dir() else []
    if len(active_dirs) > int(budgets.get("max_active_experiments", 1)):
        errors.append("too many active experiments")
    state_active = state.get("active_experiment")
    active_names = {path.name for path in active_dirs}
    if state_active and state_active not in active_names:
        errors.append("STATE.active_experiment has no active directory")
    if not state_active and active_names:
        errors.append("active directory exists but STATE.active_experiment is null")

    results_root = root / "artifacts/results"
    if results_root.is_dir():
        for result_dir in results_root.iterdir():
            if not result_dir.is_dir() or result_dir.name.startswith("."):
                continue
            if any(result_dir.iterdir()) and not (result_dir / "AGENTS.md").is_file():
                errors.append(f"missing result AGENTS.md: {result_dir.relative_to(root)}")
            prohibited = {"history.json", "train_metrics.json", "test_metrics.json"}
            for name in prohibited:
                if (result_dir / name).exists():
                    errors.append(
                        "retained intermediate artifact is prohibited: "
                        f"{result_dir.relative_to(root) / name}"
                    )

    context = root / "research/CONTEXT.md"
    if context.is_file() and len(_read_text(context)) > int(budgets.get("max_context_chars", 9000)):
        errors.append("research/CONTEXT.md exceeds the context budget")

    return errors, warnings


def main() -> int:
    try:
        parser = QuietArgumentParser(description="Validate repository structure.")
        parser.add_argument("--json", action="store_true", dest="as_json")
        args = parser.parse_args()
        root = root_from_script()
        errors, warnings = validate(root)
        if args.as_json:
            payload: dict[str, Any] = {
                "ok": not errors,
                "errors": errors,
                "warnings": warnings,
            }
            print(json.dumps(payload, separators=(",", ":")))
            return 0 if not errors else 1
        if errors:
            print(
                f"ERROR validate: RuntimeError: {one_line('; '.join(errors[:12]))}",
                file=sys.stderr,
            )
            return 1
        file_count = sum(1 for path in root.rglob("*") if path.is_file())
        print(f"OK validate files={file_count} warnings={len(warnings)}")
        return 0
    except Exception as exc:
        print(
            f"ERROR validate: {type(exc).__name__}: {one_line(exc)[:400]}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
