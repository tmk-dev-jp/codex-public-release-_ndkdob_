"""Fail closed on partial research-decision acceptance; never replay writes."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from scripts.common import atomic_write_json, read_json, safe_relative_path, sha256_file
from scripts.records import field, normalize_record_format, section

# Only accept_decision installs this context, after validating the saved response.
# It is process-local bookkeeping, not authentication or a concurrent-writer lock.
_current: ContextVar[tuple[Path, dict] | None] = ContextVar("decision_acceptance", default=None)


def _identity(root: Path, folder: Path) -> dict:
    request = read_json(folder / "REQUEST.json")
    response = read_json(folder / "RESPONSE.json")
    dispatch = read_json(folder / "DISPATCHED.json")
    if not all(isinstance(value, dict) for value in (request, response, dispatch)):
        raise ValueError("decision evidence must contain objects")
    request_hash = sha256_file(folder / "REQUEST.json")
    if dispatch.get("request_sha256") != request_hash or not dispatch.get("worker_id"):
        raise ValueError("changed or unbound decision dispatch")
    return {
        "acceptance_version": 1,
        "action": response["action"],
        "issue": request["issue"],
        "path": (folder / "RESPONSE.json").relative_to(root).as_posix(),
        "report_sha256": sha256_file(folder / "RESPONSE.json"),
        "request_sha256": request_hash,
        "dispatch_sha256": sha256_file(folder / "DISPATCHED.json"),
        "worker_id": dispatch["worker_id"],
    }


def require_decision_integrity(root: Path, experiment_id: str) -> None:
    base = safe_relative_path(root, f"review/decisions/{experiment_id}", allow_missing=True)
    folders = {
        p.parent for name in ("APPLYING.json", "ACCEPTED.json") for p in base.glob(f"*/{name}")
    }
    interpretations = {}
    for folder in sorted(folders):
        intent_path, receipt_path = folder / "APPLYING.json", folder / "ACCEPTED.json"
        request = (folder / "REQUEST.json").relative_to(root)
        try:
            receipt = read_json(receipt_path) if receipt_path.is_file() else None
            intent = read_json(intent_path) if intent_path.is_file() else None
        except (OSError, ValueError) as exc:
            raise ValueError(f"unreadable decision acceptance: request={request}") from exc
        if (
            not intent_path.is_file()
            and isinstance(receipt, dict)
            and ("acceptance_version" not in receipt)
        ):
            continue  # Historical completed decisions predate intent records.
        if not intent_path.is_file():
            raise ValueError(f"decision acceptance requires inspection: request={request}")
        try:
            matches = intent == _identity(root, folder)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"changed decision evidence: request={request}") from exc
        if not matches or (receipt is not None and receipt != intent):
            raise ValueError(f"changed decision acceptance: request={request}")
        if receipt is None and _current.get() != (folder.resolve(), intent):
            raise ValueError(f"interrupted decision acceptance: request={request}")
        if receipt is not None and receipt["action"] == "interpret":
            interpretations[folder] = receipt
    if interpretations:
        _require_evaluation_materialization(root, experiment_id, interpretations)


def _require_evaluation_materialization(root: Path, experiment_id: str, receipts: dict) -> None:
    current = _current.get()
    if current is not None and current[1]["action"] == "interpret" and (
        current[0].parent == next(iter(receipts)).resolve().parent
    ):
        return  # Only the validated operation may finish its own materialization.
    active = root / "experiments/active" / experiment_id
    if not (active / "MANIFEST.json").is_file():
        active = root / "experiments/completed" / experiment_id
    request = (next(iter(receipts)) / "REQUEST.json").relative_to(root)
    try:
        evaluation = read_json(active / "MANIFEST.json").get("evaluation")
        if not isinstance(evaluation, dict):
            raise ValueError("accepted interpretation lacks evaluation metadata")
        if evaluation.get("source") != "agent_research_decision":
            if evaluation.get("source") == "human_interpretation" and (
                "decision_provenance" not in evaluation
            ):
                return  # Explicit human acceptance replaces the current attribution.
            raise ValueError("accepted interpretation has invalid source attribution")
        selected = [folder for folder in receipts if evaluation.get("path") == (
            folder / "INTERPRETATION.md"
        ).relative_to(root).as_posix()]
        if len(selected) != 1:
            raise ValueError("evaluation does not identify its accepted interpretation")
        folder = selected[0]
        request = (folder / "REQUEST.json").relative_to(root)
        if evaluation.get("decision_provenance") != receipts[folder]:
            raise ValueError("evaluation provenance differs from its receipt")
        text = read_json(folder / "RESPONSE.json")["interpretation"]
        for path in (folder / "INTERPRETATION.md", active / "EVALUATION.md"):
            if path.read_bytes() != text.encode("utf-8"):
                raise ValueError("materialized interpretation differs from its response")
        expected = normalize_record_format(text)
        recorded = normalize_record_format((active / "EXPERIMENT.md").read_text(encoding="utf-8"))
        for heading in ("## Conclusion", "## Issues and Next Direction"):
            if section(recorded, heading) != section(expected, heading):
                raise ValueError("copied evaluation section differs from its response")
        expected_decision = field(section(expected, "## Conclusion"), "Decision").lower()
        if evaluation.get("decision") != expected_decision:
            raise ValueError("manifest decision differs from its response")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"changed decision materialization: request={request}: {exc}") from exc


def require_routing_integrity(root: Path, state: dict) -> None:
    targets = {state.get("active_experiment"), state.get("latest_completed_experiment")}
    for name in ("agent_led_loop", "unattended_loop"):
        targets.add(state.get(name, {}).get("target_experiment"))
    for target in sorted(target for target in targets if target):
        require_decision_integrity(root, target)


def _is_accepting(folder: Path) -> bool:
    current = _current.get()
    return current is not None and current[0] == folder.resolve()


def _begin_acceptance(root: Path, folder: Path) -> None:
    current = _current.get()
    if current is None or current != (folder.resolve(), _identity(root, folder)):
        raise ValueError("acceptance requires the validated in-process decision")
    path = folder / "APPLYING.json"
    if path.exists():
        raise ValueError("decision acceptance already started")
    atomic_write_json(path, current[1])


@contextmanager
def _accepting(root: Path, folder: Path):
    if _current.get() is not None:
        raise ValueError("nested decision acceptance is not supported")
    metadata = _identity(root, folder)
    token = _current.set((folder.resolve(), metadata))
    try:
        yield metadata
    finally:
        _current.reset(token)
