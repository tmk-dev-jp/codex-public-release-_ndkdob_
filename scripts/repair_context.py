"""Prepare bounded repair inputs and report completion without exposing debugging history."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_implementation_review_bundle import implementation_audit_input_hashes
from scripts.build_plan_review_bundle import require_accepted_plan_audit
from scripts.build_review_bundle import audit_input_hashes
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_file,
    sha256_path_set,
)
from scripts.implementation_delta import require_current_implementation_delta
from scripts.records import IMPLEMENTATION_PROFILES, field, plan_hash
from scripts.workflow import comparison_results_recorded, require_active

MAX_REQUEST_CHARS = 6000


def request_path(root: Path, experiment_id: str, sequence: int) -> Path:
    return safe_relative_path(
        root,
        f"review/repairs/{experiment_id}/attempt-{sequence:03d}/REQUEST.json",
        allow_missing=True,
    )


def _locked_inputs(root: Path, active: Path, manifest: dict) -> dict:
    config = safe_relative_path(root, manifest["config"])
    hashes = {
        "plan_sha256": plan_hash(active / "EXPERIMENT.md", config, active / "SCOPE.json"),
        "config_sha256": sha256_file(config),
        "scope_sha256": sha256_file(active / "SCOPE.json"),
    }
    if hashes["plan_sha256"] != manifest.get("plan_sha256"):
        raise ValueError("locked plan or scope changed before repair")
    if hashes["config_sha256"] != manifest.get("locked_config_sha256"):
        raise ValueError("locked config changed before repair")
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    return hashes


def _failure(root: Path, active: Path, manifest: dict) -> dict:
    for kind, name in (
        ("implementation_audit", "IMPLEMENTATION_AUDIT.md"),
        ("integrity_audit", "INTEGRITY_AUDIT.md"),
    ):
        audit = manifest.get(kind)
        if not isinstance(audit, dict) or audit.get("verdict") != "fail":
            continue
        path = active / name
        if sha256_file(path) != audit.get("audit_sha256"):
            raise ValueError("failed audit changed before repair")
        if path.stat().st_size > MAX_REQUEST_CHARS:
            raise ValueError("failed audit is too large for a compact repair context")
        text = path.read_text(encoding="utf-8")
        inputs = (
            implementation_audit_input_hashes
            if kind == "implementation_audit"
            else audit_input_hashes
        )
        if field(text, "Verdict").lower() != "fail" or audit.get("audited_inputs") != inputs(
            root, active, manifest
        ):
            raise ValueError("failed audit inputs changed before repair")
        return {
            "kind": kind,
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "blocking_issue": field(text, "Blocking issue"),
            "required_action": field(text, "Required action"),
        }
    path = safe_relative_path(root, manifest["result_dir"]) / "error.json"
    if path.stat().st_size > MAX_REQUEST_CHARS:
        raise ValueError("error artifact is too large for a compact repair context")
    error = read_json(path)
    if error.get("experiment_id") != manifest["id"]:
        raise ValueError("failure experiment ID differs")
    if set(error) - {"schema_version", "experiment_id", "phase", "error_type", "message"}:
        raise ValueError("repair requires a compact error artifact without transcripts")
    for key in ("error_type", "message"):
        if not isinstance(error.get(key), str) or len(error[key]) > 400:
            raise ValueError("repair error fields must be compact strings")
    return {
        "kind": "execution_error",
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "error": error,
    }


def repair_request(root: Path, experiment_id: str) -> dict:
    state, manifest = require_active(root, experiment_id, {"FAILED"})
    if state.get("next_action", {}).get("mode") != "debug_failure":
        raise ValueError("next action is not debug_failure")
    if comparison_results_recorded(root, manifest):
        raise ValueError("recorded comparison requires a human disposition")
    active = root / "experiments/active" / experiment_id
    locked = _locked_inputs(root, active, manifest)
    delta = require_current_implementation_delta(root, active, manifest)
    profile = field(
        (active / "EXPERIMENT.md").read_text(encoding="utf-8"), "Implementation profile"
    )
    profile = profile.lower()
    if profile not in IMPLEMENTATION_PROFILES:
        raise ValueError("invalid locked implementation profile")
    scope = read_json(active / "SCOPE.json")
    failure = _failure(root, active, manifest)
    request = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "profile": profile,
        "sequence": len(delta.get("repairs", [])) + 1,
        "locked_inputs": locked,
        "before_implementation_sha256": sha256_path_set(root, manifest["implementation_files"]),
        "delta_sha256": sha256_file(active / "IMPLEMENTATION_DELTA.json"),
        "failure": failure,
        "read_first": [
            f"experiments/active/{experiment_id}/EXPERIMENT.md",
            manifest["config"],
            f"experiments/active/{experiment_id}/SCOPE.json",
        ],
        "change_targets": scope["change_targets"],
        "implementation_entry_reads": scope.get("implementation_entry_reads", []),
        "procedure": "automation/ISOLATED_REPAIR.md",
        "context": "Fresh worker only; no supervisor or prior worker conversation.",
        "return": "Only repair_context.py status output; no source, logs or investigation.",
    }
    if len(json.dumps(request, indent=2)) + 1 > MAX_REQUEST_CHARS:
        raise ValueError("repair request exceeds 6000 characters")
    return request


def prepare_repair_context(root: Path, experiment_id: str) -> Path:
    request = repair_request(root, experiment_id)
    path = request_path(root, experiment_id, request["sequence"])
    if path.exists() and read_json(path) != request:
        raise ValueError("prepared repair context changed; do not overwrite it")
    if not path.exists():
        atomic_write_json(path, request)
    manifest_path = root / "experiments/active" / experiment_id / "MANIFEST.json"
    manifest = read_json(manifest_path)
    metadata = {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "sequence": request["sequence"],
    }
    previous = manifest.get("repair_context")
    if previous and previous.get("sequence") == request["sequence"] and previous != metadata:
        raise ValueError("prepared repair context hash changed")
    manifest["repair_context"] = metadata
    atomic_write_json(manifest_path, manifest)
    return path


def repair_status(root: Path, experiment_id: str) -> str:
    state, manifest = require_active(root, experiment_id, {"FAILED", "IMPLEMENTED"})
    if state["phase"] == "FAILED":
        return f"{experiment_id} status=not_completed next=review-worker-blocker"
    active = root / "experiments/active" / experiment_id
    delta = require_current_implementation_delta(root, active, manifest)
    repairs = delta.get("repairs", [])
    if not repairs:
        raise ValueError("no completed repair is recorded")
    path = request_path(root, experiment_id, len(repairs))
    expected = {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "sequence": len(repairs),
    }
    if manifest.get("repair_context") != expected:
        raise ValueError("prepared repair context hash changed")
    request = read_json(path)
    if request.get("experiment_id") != experiment_id or request.get("sequence") != len(repairs):
        raise ValueError("repair request identity differs")
    if request["locked_inputs"] != _locked_inputs(root, active, manifest):
        raise ValueError("repair inputs changed after delegation")
    if sha256_path_set(root, manifest["implementation_files"]) != manifest["implementation_sha256"]:
        raise ValueError("repaired implementation changed after recording")
    changed = len(repairs[-1]["targets"])
    return (
        f"{experiment_id} status=implemented repair={len(repairs)} changed_files={changed} "
        f"next={state['next_action']['mode']}"
    )


def _execute() -> str:
    parser = QuietArgumentParser(
        description="Prepare or inspect an isolated implementation repair."
    )
    parser.add_argument("action", choices=["prepare", "status"])
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    if args.action == "prepare":
        return prepare_repair_context(root, args.experiment_id).relative_to(root).as_posix()
    return repair_status(root, args.experiment_id)


if __name__ == "__main__":
    raise SystemExit(run_script("repair-context", _execute))
