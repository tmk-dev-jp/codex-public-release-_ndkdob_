from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dl_research.config import load_config
from scripts.build_context import build_context
from scripts.build_decision_facts import require_current_decision_facts
from scripts.build_review_bundle import require_accepted_integrity_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
)
from scripts.decision_integrity import _begin_acceptance, _identity, _is_accepting
from scripts.records import (
    field,
    normalize_record_format,
    replace_section,
    require_filled,
    section,
    validate_conclusion,
    validate_record_word_limits,
)
from scripts.workflow import experiment_manifest_path, require_active, set_phase

JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    return section(normalize_record_format(text), heading, until=next_heading)


def accept_interpretation(
    root: Path, experiment_id: str, path: Path, *, source: str,
    decision_path: Path | None = None,
) -> Path:
    if source not in {"human_interpretation", "agent_research_decision"}:
        raise ValueError("unknown interpretation source")
    if source == "agent_research_decision":
        from scripts.research_decision import accept_decision, require_interpretation_decision

        if decision_path is None:
            raise ValueError("agent interpretation requires a current dispatched research decision")
        require_interpretation_decision(root, experiment_id, decision_path, path)
        if not _is_accepting(decision_path):
            accept_decision(root, experiment_id, "interpretation", read_json(
                decision_path / "REQUEST.json",
            ).get("question", ""))
            return path
    state, manifest = require_active(
        root,
        experiment_id,
        {"TRAINED", "REVIEW_REQUIRED", "READY_TO_FINALIZE"},
    )
    if not path.is_file():
        raise FileNotFoundError(f"interpretation not found: {path.relative_to(root)}")
    text = path.read_text(encoding="utf-8")
    config = load_config(root / manifest["config"])
    active = root / "experiments/active" / experiment_id
    facts = require_current_decision_facts(root, active, manifest)
    if config.experiment.review_mode == "independent":
        require_accepted_integrity_audit(root, active, manifest)
    conclusion = _section(text, "## Conclusion", "## Issues and Next Direction")
    issues = _section(
        text, "## Issues and Next Direction",
        "## Japanese Notes" if source == "human_interpretation" else None,
    )
    copied_text = conclusion + "\n" + issues
    if JAPANESE.search(copied_text):
        raise ValueError("English required fields must not contain Japanese; use Japanese Notes")
    if re.search(r"<[A-Za-z][^>\n]*>", copied_text):
        raise ValueError("human interpretation still contains template placeholders")
    for label in [
        "Decision",
        "Mechanical rule status",
        "Decision-rule assessment",
        "Primary result",
        "Baseline comparison",
        "Supported scope",
        "Unsupported or missing evidence",
        "Confidence and caveats",
        "Main issue",
        "Next action",
        "Stop condition",
    ]:
        require_filled(field(copied_text, label), label)
    decision = field(copied_text, "Decision").lower()
    if decision not in {"support", "reject", "inconclusive"}:
        raise ValueError("Decision must be support, reject, or inconclusive")
    mechanical_status = field(copied_text, "Mechanical rule status").lower()
    expected_status = str(facts["decision_rule"]["status"]).lower()
    if mechanical_status != expected_status:
        raise ValueError(
            f"Mechanical rule status must be {expected_status}; "
            f"found {mechanical_status}"
        )

    record_path = active / "EXPERIMENT.md"
    record = record_path.read_text(encoding="utf-8")
    record = replace_section(record, "## Conclusion", conclusion)
    record = replace_section(record, "## Issues and Next Direction", issues)
    if source == "agent_research_decision":
        validate_conclusion(record)
        validate_record_word_limits(
            record,
            maximum_plan_words=int(state.get("budgets", {}).get("max_experiment_plan_words", 700)),
            maximum_conclusion_words=int(
                state.get("budgets", {}).get("max_experiment_conclusion_words", 400)
            ),
        )
    if source == "agent_research_decision":
        _begin_acceptance(root, decision_path)
    atomic_write_text(record_path, record)
    atomic_write_text(active / "EVALUATION.md", text)
    manifest["evaluation"] = {
        "path": path.relative_to(root).as_posix(),
        "decision": decision,
        "source": source,
    }
    if source == "agent_research_decision":
        manifest["evaluation"]["decision_provenance"] = _identity(root, decision_path)
    atomic_write_json(experiment_manifest_path(root, experiment_id), manifest)

    if state.get("phase") != "READY_TO_FINALIZE":
        set_phase(
            root,
            experiment_id,
            "READY_TO_FINALIZE",
            objective=f"Finalize the experiment with the accepted {source}.",
            review_required=False,
        )
    else:
        state["next_action"] = {
            "mode": "ready_to_finalize",
            "queue_id": manifest.get("queue_id"),
            "objective": f"Finalize the experiment with the accepted {source}.",
        }
        state["review_required"] = False
        atomic_write_json(root / "research/STATE.json", state)
        build_context(root)
    return path


def accept_human_interpretation(root: Path, experiment_id: str) -> Path:
    return accept_interpretation(
        root, experiment_id, root / "human/results" / experiment_id / "INTERPRETATION.md",
        source="human_interpretation",
    )


def _execute() -> str:
    parser = QuietArgumentParser(description="Accept one human-written result interpretation.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return accept_human_interpretation(root, args.experiment_id).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("accept-human-interpretation", _execute))
