"""Bounded, source-attributed research decisions for the separate agent-led loop."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_decision_facts import require_current_decision_facts
from scripts.build_plan_review_bundle import plan_audit_input_hashes
from scripts.build_review_bundle import require_accepted_integrity_audit
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)
from scripts.decision_integrity import _accepting, _begin_acceptance
from scripts.records import plan_hash, plan_record_material, require_filled
from scripts.research_memory import (
    append_jsonl,
    latest_novelty,
    novelty_contract_required,
    novelty_evidence_errors,
)
from scripts.workflow import require_active

ISSUES = {"novelty", "plan", "design", "interpretation"}
MAX_DECISIONS = 6
MAX_REVISIONS = 2


def _base(root: Path, experiment_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", experiment_id):
        raise ValueError("invalid experiment ID")
    return safe_relative_path(root, f"review/decisions/{experiment_id}", allow_missing=True)


def _snapshot(root: Path, experiment_id: str, issue: str, question: str) -> dict:
    if issue not in ISSUES:
        raise ValueError("unknown research decision issue")
    phases = {"REVIEW_REQUIRED", "READY_TO_FINALIZE"} if issue == "interpretation" else {
        "DRAFT", "PLANNED",
    }
    state, manifest = require_active(root, experiment_id, phases)
    require_contribution = novelty_contract_required(manifest)
    control = state.get("agent_led_loop", {})
    if control.get("status") != "in_progress" or control.get("target_experiment") != experiment_id:
        raise ValueError("agent-led router must bind this target first")
    active = root / "experiments/active" / experiment_id
    config_path = safe_relative_path(root, manifest["config"])
    if state["phase"] != "DRAFT" and plan_hash(
        active / "EXPERIMENT.md", config_path, active / "SCOPE.json",
    ) != manifest.get("plan_sha256"):
        raise ValueError("locked plan changed")
    if issue == "plan":
        if state.get("next_action", {}).get("mode") != "review_experiment_plan":
            raise ValueError("plan decision requires completed independent audit")
        audit = manifest.get("plan_audit") or {}
        if audit.get("verdict") not in {"pass", "warn", "fail"} or (
            audit.get("audit_sha256") != sha256_file(active / "PLAN_AUDIT.md")
            or audit.get("audited_inputs") != plan_audit_input_hashes(root, active, manifest)
        ):
            raise ValueError("missing or stale accepted plan audit")
    sources = {}
    paths = ["research/GOAL.md", f"experiments/active/{experiment_id}/EXPERIMENT.md",
             manifest["config"], f"experiments/active/{experiment_id}/SCOPE.json"]
    for relative in ("research/planning/HYPOTHESIS_POLICY.md",
                     f"experiments/active/{experiment_id}/PLAN_AUDIT.md",
                     f"experiments/active/{experiment_id}/RESEARCH_GUIDANCE.md"):
        if issue == "interpretation" and relative.endswith("RESEARCH_GUIDANCE.md"):
            continue
        if (root / relative).is_file():
            paths.append(relative)
    for relative in paths:
        path = safe_relative_path(root, relative)
        sources[relative] = (
            json.dumps(read_json(path), separators=(",", ":"))
            if path.suffix == ".json" else path.read_text(encoding="utf-8")
        )
        if path == active / "EXPERIMENT.md":
            sources[relative] = plan_record_material(sources[relative])
    facts = None
    if issue == "interpretation":
        facts = require_current_decision_facts(root, active, manifest)
        if read_json(config_path).get("experiment", {}).get("review_mode") == "independent":
            require_accepted_integrity_audit(root, active, manifest)
            sources[f"experiments/active/{experiment_id}/INTEGRITY_AUDIT.md"] = (
                active / "INTEGRITY_AUDIT.md"
            ).read_text(encoding="utf-8")
        sources[f"experiments/active/{experiment_id}/DECISION_FACTS.json"] = json.dumps(
            facts, separators=(",", ":"),
        )
    audits = {
        name: {key: value.get(key) for key in ("verdict", "audit_sha256")}
        if isinstance(value := manifest.get(name), dict) else None
        for name in ("plan_audit", "integrity_audit")
    }
    return {
        "schema_version": "1.1", "experiment_id": experiment_id, "issue": issue,
        **({"novelty_contract_version": manifest["novelty_contract_version"]}
           if require_contribution else {}),
        "question": question, "phase": state["phase"], "mode": state["next_action"]["mode"],
        "plan_sha256": manifest.get("plan_sha256"), "sources": sources,
        "novelty": latest_novelty(root, experiment_id),
        **audits,
        "budgets": state.get("budgets", {}), "execution_policy": state.get("execution_policy", {}),
    }


def _location(root: Path, experiment_id: str, snapshot: dict) -> Path:
    digest = sha256_bytes(json.dumps(snapshot, sort_keys=True).encode())
    return _base(root, experiment_id) / digest


def _valid_worker_id(value: object) -> bool:
    # Collaboration backends return either an opaque ID or a canonical task name.
    return isinstance(value, str) and bool(re.fullmatch(
        r"/?[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", value,
    ))


def _pending_action(root: Path, folder: Path, reason: str) -> str:
    dispatched = read_json(folder / "DISPATCHED.json")
    request = folder / "REQUEST.json"
    if not request.is_file() or dispatched.get("request_sha256") != sha256_file(request):
        return "action=blocked reason=changed-dispatched-request"
    worker = dispatched.get("worker_id")
    if worker is None:
        return f"action=blocked reason={reason} request={request.relative_to(root)}"
    if not _valid_worker_id(worker):
        return "action=blocked reason=invalid-decision-worker-id"
    # A stored identity is not proof that the worker is live.
    return (
        f"action=check-worker worker_id={worker} reason={reason} "
        f"request={request.relative_to(root)}"
    )


def decision_action(
    root: Path, experiment_id: str, issue: str, *, question: str = "",
    explicit_user_request: bool = False,
) -> str:
    if not explicit_user_request:
        return "action=blocked reason=explicit-agent-led-request-required"
    snapshot = _snapshot(root, experiment_id, issue, question)
    folder = _location(root, experiment_id, snapshot)
    request = folder / "REQUEST.json"
    base = _base(root, experiment_id)
    for prior_request in base.glob("*/REQUEST.json"):
        if not (prior_request.parent / "ACCEPTED.json").is_file() and (
            read_json(prior_request).get("schema_version") != snapshot["schema_version"]
        ):
            return "action=blocked reason=legacy-decision-request-requires-review"
    dispatched = list(base.glob("*/DISPATCHED.json"))
    for path in sorted(dispatched):
        if path.parent != folder and not (path.parent / "RESPONSE.json").is_file():
            return _pending_action(root, path.parent, "another-decision-worker-pending")
    if not request.is_file():
        if len(dispatched) >= MAX_DECISIONS:
            return "action=blocked reason=research-decision-budget-exhausted"
        return f"action=build builder=research_decision issue={issue}"
    if read_json(request) != snapshot:
        return "action=blocked reason=changed-decision-request"
    if (folder / "ACCEPTED.json").is_file():
        accepted = read_json(folder / "ACCEPTED.json")
        if accepted["report_sha256"] != sha256_file(folder / "RESPONSE.json"):
            return "action=blocked reason=changed-accepted-decision"
        return f"action=blocked reason=decision-already-applied outcome={accepted['action']}"
    if (folder / "RESPONSE.json").is_file():
        return f"action=accept acceptor=research_decision request={request.relative_to(root)}"
    if (folder / "DISPATCHED.json").is_file():
        return _pending_action(root, folder, "decision-worker-pending-or-unavailable")
    if len(dispatched) >= MAX_DECISIONS:
        return "action=blocked reason=research-decision-budget-exhausted"
    return (
        "action=delegate agent=default model=gpt-6-astra reasoning=high read_only=true "
        f"request={request.relative_to(root)}"
    )


def prepare_decision(root: Path, experiment_id: str, issue: str, question: str = "") -> Path:
    action = decision_action(
        root, experiment_id, issue, question=question, explicit_user_request=True,
    )
    if not action.startswith("action=build "):
        raise ValueError(f"decision preparation is not permitted: {action}")
    snapshot = _snapshot(root, experiment_id, issue, question)
    maximum = int(snapshot["budgets"].get("max_plan_audit_chars", 9000))
    serialized = json.dumps(snapshot, separators=(",", ":")) + "\n"
    if len(serialized) > maximum:
        raise ValueError(f"research decision request exceeds {maximum} chars")
    path = _location(root, experiment_id, snapshot) / "REQUEST.json"
    atomic_write_text(path, serialized)
    return path


def dispatch_decision(root: Path, experiment_id: str, issue: str, question: str = "") -> Path:
    action = decision_action(
        root, experiment_id, issue, question=question, explicit_user_request=True,
    )
    if not action.startswith("action=delegate "):
        raise ValueError(f"decision dispatch is not permitted: {action}")
    snapshot = _snapshot(root, experiment_id, issue, question)
    folder = _location(root, experiment_id, snapshot)
    path = folder / "DISPATCHED.json"
    atomic_write_json(path, {"request_sha256": sha256_file(folder / "REQUEST.json")})
    return path


def bind_worker(
    root: Path, experiment_id: str, issue: str, question: str = "", *, worker_id: str,
) -> Path:
    """Record the returned worker handle, never infer its liveness or replace it."""
    if not _valid_worker_id(worker_id):
        raise ValueError("invalid decision worker ID")
    snapshot = _snapshot(root, experiment_id, issue, question)
    folder = _location(root, experiment_id, snapshot)
    request = folder / "REQUEST.json"
    path = folder / "DISPATCHED.json"
    dispatched = read_json(path)
    if read_json(request) != snapshot or dispatched.get("request_sha256") != sha256_file(request):
        raise ValueError("research decision request changed after dispatch")
    if (folder / "ACCEPTED.json").exists():
        raise ValueError("research decision already accepted")
    if dispatched.get("worker_id") == worker_id:
        return path
    if "worker_id" in dispatched:
        raise ValueError("cannot replace a dispatched decision worker")
    atomic_write_json(path, {**dispatched, "worker_id": worker_id})
    return path


def _valid_evidence_ref(ref: object, snapshot: dict) -> bool:
    if not isinstance(ref, str):
        return False
    if ref in snapshot["sources"]:
        return True
    if snapshot["issue"] != "novelty" or any(char.isspace() for char in ref):
        return False
    url = urlsplit(ref)
    return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password


def _validate_assessment(response: dict, snapshot: dict) -> None:
    assessment = response.get("assessment")
    if not isinstance(assessment, dict):
        raise ValueError("decision requires an evidence assessment")
    for name in ("counterargument", "uncertainty", "change_condition"):
        value = assessment.get(name)
        if not isinstance(value, str):
            raise ValueError(f"assessment {name} must be text")
        require_filled(value, f"assessment {name}")
    observations = assessment.get("observations")
    if not isinstance(observations, list) or not 1 <= len(observations) <= 6:
        raise ValueError("assessment requires one to six cited observations")
    cited = set()
    for observation in observations:
        if not isinstance(observation, dict) or not _valid_evidence_ref(
            observation.get("source"), snapshot,
        ):
            raise ValueError("assessment observation requires an allowed source")
        value = observation.get("observation")
        if not isinstance(value, str):
            raise ValueError("assessment observation must be text")
        require_filled(value, "assessment observation")
        cited.add(observation["source"])
    if cited != set(response["evidence_refs"]):
        raise ValueError("assessment sources must match evidence_refs")
    prefix = f"experiments/active/{snapshot['experiment_id']}/"
    if response.get("action") == "approve" and snapshot["issue"] == "plan":
        required = {prefix + "EXPERIMENT.md", prefix + "PLAN_AUDIT.md"}
        if not required.issubset(cited):
            raise ValueError("plan approval must assess the plan and accepted audit")
        value = assessment.get("audit_response")
        if not isinstance(value, str):
            raise ValueError("plan approval requires an audit_response")
        require_filled(value, "assessment audit_response")
    if response.get("action") == "interpret" and prefix + "DECISION_FACTS.json" not in cited:
        raise ValueError("interpretation must assess authoritative decision facts")


def _response(folder: Path, snapshot: dict) -> dict:
    dispatched = read_json(folder / "DISPATCHED.json")
    if dispatched.get("request_sha256") != sha256_file(folder / "REQUEST.json"):
        raise ValueError("research decision request changed after dispatch")
    worker = dispatched.get("worker_id")
    if not _valid_worker_id(worker):
        raise ValueError("decision requires a bound worker ID")
    response = read_json(folder / "RESPONSE.json")
    if not isinstance(response, dict):
        raise ValueError("decision response must be an object")
    maximum = 400 if snapshot["issue"] == "interpretation" else 250
    if len(json.dumps(response).split()) > maximum:
        raise ValueError(f"research decision exceeds {maximum} words")
    require_filled(response.get("rationale", ""), "decision rationale")
    refs = response.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(
        not _valid_evidence_ref(ref, snapshot) for ref in refs
    ):
        raise ValueError("decision requires supplied evidence paths or scoped novelty URLs")
    if len(refs) != len(set(refs)):
        raise ValueError("decision evidence_refs must be distinct sources")
    _validate_assessment(response, snapshot)
    return response


def accept_decision(root: Path, experiment_id: str, issue: str, question: str = "") -> Path:
    snapshot = _snapshot(root, experiment_id, issue, question)
    folder = _location(root, experiment_id, snapshot)
    if read_json(folder / "REQUEST.json") != snapshot:
        raise ValueError("stale research decision request")
    if (folder / "ACCEPTED.json").exists():
        raise ValueError("research decision already accepted")
    response = _response(folder, snapshot)
    state, _ = require_active(root, experiment_id, {snapshot["phase"]})
    with _accepting(root, folder) as metadata:
        _apply_response(root, experiment_id, issue, folder, snapshot, response, state, metadata)
        atomic_write_json(folder / "ACCEPTED.json", metadata)
    return folder / "ACCEPTED.json"


def _apply_response(root, experiment_id, issue, folder, snapshot, response, state, metadata):
    action = response.get("action")
    active = root / "experiments/active" / experiment_id
    if action == "revise" and issue in {"novelty", "plan", "design"}:
        instructions = response.get("instructions", "")
        if isinstance(instructions, list):
            for instruction in instructions:
                require_filled(instruction, "revision instruction")
            instructions = "\n\n".join(instructions)
        require_filled(instructions, "revision instructions")
        revisions = sum(
            read_json(path).get("action") == "revise"
            for path in _base(root, experiment_id).glob("*/ACCEPTED.json")
        )
        if revisions >= MAX_REVISIONS:
            raise ValueError("research revision budget exhausted")
        _begin_acceptance(root, folder)
        if state["phase"] == "PLANNED":
            from scripts.return_plan_to_draft import return_plan_to_draft

            return_plan_to_draft(root, experiment_id)
        atomic_write_text(active / "RESEARCH_GUIDANCE.md", instructions + "\n")
    elif action == "approve" and issue == "plan":
        from scripts.approve_plan import approve_plan
        from scripts.next_autonomous_step import novelty_block_reason

        if novelty_block_reason(root, experiment_id) is not None:
            raise ValueError("novelty must be cleared before plan approval")
        # The approval entry point revalidates this report and current audit.
        approve_plan(root, experiment_id, "agent_research_decision", decision_path=folder)
    elif action == "record_novelty" and issue == "novelty":
        novelty = response.get("novelty", {})
        previous = snapshot["novelty"] or {}
        if previous.get("risk") in ("high", "block") or previous.get("decision") == "reject":
            revised = False
            for accepted in _base(root, experiment_id).glob("*/ACCEPTED.json"):
                if read_json(accepted).get("action") != "revise":
                    continue
                original = read_json(accepted.parent / "REQUEST.json")
                if original["novelty"] == previous and (
                    original["plan_sha256"] != snapshot["plan_sha256"]
                    and snapshot["phase"] == "PLANNED"
                ):
                    revised = True
            if not revised:
                raise ValueError(
                    "high-risk or rejected novelty requires a substantive plan revision"
                )
            require_filled(response.get("resolved_objection", ""), "resolved novelty objection")
        if (
            not isinstance(novelty, dict)
            or novelty.get("experiment_id") != experiment_id
            or novelty.get("risk") not in ("low", "medium")
            or novelty.get("decision") != "proceed"
            or novelty_evidence_errors(
                novelty, require_contribution=novelty_contract_required(snapshot),
            )
        ):
            raise ValueError("novelty decision lacks complete source-backed evidence")
        novelty["source"] = "agent_research_decision"
        novelty["decision_report"] = metadata["path"]
        _begin_acceptance(root, folder)
        append_jsonl(root / "research/novelty/NOVELTY_CHECKS.jsonl", novelty)
        if state["phase"] == "PLANNED":
            state["next_action"]["mode"] = "audit_experiment_plan"
            state.setdefault("approvals", {})["plan_review_experiment_id"] = None
            atomic_write_json(root / "research/STATE.json", state)
    elif action == "interpret" and issue == "interpretation":
        from scripts.accept_human_interpretation import accept_interpretation

        text = response.get("interpretation", "")
        require_filled(text, "interpretation")
        path = folder / "INTERPRETATION.md"
        atomic_write_text(path, text)
        accept_interpretation(
            root, experiment_id, path, source="agent_research_decision", decision_path=folder,
        )
    elif action != "stop":
        raise ValueError("decision action is not valid for this issue")
    else:
        _begin_acceptance(root, folder)


def _require_decision(
    root: Path, experiment_id: str, folder: Path, issue: str, action: str,
) -> dict:
    if (folder / "ACCEPTED.json").exists():
        raise ValueError("research decision already accepted")
    snapshot = read_json(folder / "REQUEST.json")
    expected = _snapshot(root, experiment_id, issue, snapshot.get("question", ""))
    if (
        folder.resolve() != _location(root, experiment_id, expected).resolve()
        or snapshot != expected
    ):
        raise ValueError(f"{issue} decision is not current for this target")
    response = _response(folder, snapshot)
    if response.get("action") != action:
        raise ValueError(f"{issue} decision did not {action}")
    return response


def require_plan_decision(root: Path, experiment_id: str, folder: Path) -> None:
    _require_decision(root, experiment_id, folder, "plan", "approve")


def require_interpretation_decision(
    root: Path, experiment_id: str, folder: Path, path: Path,
) -> None:
    response = _require_decision(root, experiment_id, folder, "interpretation", "interpret")
    if path.resolve() != (folder / "INTERPRETATION.md").resolve() or (
        path.read_bytes() != response.get("interpretation", "").encode("utf-8")
    ):
        raise ValueError("interpretation must match the dispatched decision's exact bytes and path")


def _execute() -> str:
    parser = QuietArgumentParser(description="Prepare, dispatch or accept agent research judgment.")
    parser.add_argument("action", choices=["gate", "prepare", "dispatch", "bind-worker", "accept"])
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--issue", required=True, choices=sorted(ISSUES))
    parser.add_argument("--question", default="")
    parser.add_argument("--worker-id")
    parser.add_argument("--explicit-user-request", action="store_true")
    args = parser.parse_args()
    if not args.explicit_user_request:
        return "action=blocked reason=explicit-agent-led-request-required"
    root = root_from_script()
    if args.action == "bind-worker":
        if not args.worker_id:
            raise ValueError("bind-worker requires --worker-id")
        return bind_worker(
            root, args.experiment_id, args.issue, args.question, worker_id=args.worker_id,
        ).relative_to(root).as_posix()
    if args.worker_id is not None:
        raise ValueError("--worker-id is only valid with bind-worker")
    if args.action == "gate":
        return decision_action(
            root, args.experiment_id, args.issue, question=args.question,
            explicit_user_request=True,
        )
    function = {"prepare": prepare_decision, "dispatch": dispatch_decision,
                "accept": accept_decision}[args.action]
    path = function(root, args.experiment_id, args.issue, args.question)
    return path.relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("research-decision", _execute))
