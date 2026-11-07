from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dl_research.experiment.comparison import require_comparison_budget
from scripts.common import (
    QuietArgumentParser,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)
from scripts.compress_audit_material import bounded_audit_request
from scripts.implementation_delta import (
    compact_implementation_delta,
    declared_implementation_delta_hash,
    require_locked_implementation_delta,
)
from scripts.records import plan_hash, plan_record_material, validate_plan
from scripts.research_memory import (
    latest_novelty,
    novelty_contract_required,
    novelty_evidence_errors,
)
from scripts.workflow import require_active


class PlanAuditRequiredError(ValueError):
    pass


def _baseline_payload(root: Path, baseline_id: str | None) -> dict:
    if baseline_id is None:
        return {"status": "not_configured", "baseline_id": None}

    registered = safe_relative_path(
        root,
        f"baselines/records/{baseline_id}.json",
        allow_missing=True,
    )
    if registered.is_file():
        return {
            "status": "available",
            "kind": "registered",
            "baseline_id": baseline_id,
            "record": read_json(registered),
        }

    index = read_json(root / "experiments/INDEX.json")
    for item in index.get("experiments", []):
        if item.get("id") != baseline_id:
            continue
        metrics = item.get("metrics")
        if isinstance(metrics, str):
            path = safe_relative_path(root, metrics, allow_missing=True)
            if path.is_file():
                return {
                    "status": "available",
                    "kind": "experiment",
                    "baseline_id": baseline_id,
                    "metrics": read_json(path),
                }
        break
    return {"status": "missing", "baseline_id": baseline_id}


def _payload_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def _auditable_config(config: dict) -> dict:
    payload = json.loads(json.dumps(config))
    payload.get("data", {})["batch_size"] = "managed_by_training_controls"
    payload.get("train", {}).get("optimizer", {})[
        "learning_rate"
    ] = "managed_by_training_controls"
    return payload


def _scientific_plan_hash(
    record_path: Path,
    config: dict,
    scope_path: Path,
) -> str:
    digest = hashlib.sha256()
    digest.update(
        plan_record_material(record_path.read_text(encoding="utf-8")).encode(
            "utf-8"
        )
    )
    digest.update(b"\0config\0")
    digest.update(
        json.dumps(
            _auditable_config(config),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    digest.update(b"\0scope\0")
    digest.update(scope_path.read_bytes())
    return digest.hexdigest()


def _training_control_policy(root: Path) -> dict:
    payload = read_json(root / "research/TRAINING_CONTROLS.json")
    return {
        "schema_version": payload.get("schema_version"),
        "policy": payload.get("policy", {}),
    }


def plan_audit_input_hashes(
    root: Path,
    active: Path,
    manifest: dict,
) -> dict[str, str]:
    require_contribution = novelty_contract_required(manifest)
    novelty = latest_novelty(root, manifest["id"])
    if require_contribution and (
        novelty_evidence_errors(novelty, require_contribution=True)
        or novelty.get("risk") not in ("low", "medium")
        or novelty.get("decision") != "proceed"
    ):
        raise PlanAuditRequiredError("plan audit requires complete source-backed contribution")
    config_path = root / manifest["config"]
    config = read_json(config_path)
    baseline = _baseline_payload(root, manifest.get("baseline_id"))
    training_control_policy = _training_control_policy(root)
    return {
        **({"novelty_contract_sha256": _payload_hash(manifest["novelty_contract_version"])}
           if require_contribution else {}),
        "plan_sha256": _scientific_plan_hash(
            active / "EXPERIMENT.md", config, active / "SCOPE.json"
        ),
        "goal_sha256": sha256_file(root / "research/GOAL.md"),
        "novelty_sha256": _payload_hash(novelty),
        "baseline_sha256": _payload_hash(baseline),
        "training_control_policy_sha256": _payload_hash(
            training_control_policy
        ),
        "implementation_delta_declared_sha256": (
            declared_implementation_delta_hash(root, active, manifest)
        ),
    }


def require_accepted_plan_audit(
    root: Path,
    active: Path,
    manifest: dict,
    *,
    allow_warn: bool,
) -> None:
    audit = manifest.get("plan_audit")
    allowed = {"pass", "warn"} if allow_warn else {"pass"}
    if not isinstance(audit, dict) or audit.get("verdict") not in allowed:
        required = "pass or warn" if allow_warn else "pass"
        raise PlanAuditRequiredError(
            f"accepted plan audit verdict {required} is required"
        )
    audit_path = active / "PLAN_AUDIT.md"
    if not audit_path.is_file() or audit.get("audit_sha256") != sha256_file(
        audit_path
    ):
        raise PlanAuditRequiredError("accepted plan audit changed after acceptance")
    if audit.get("audited_inputs") != plan_audit_input_hashes(
        root,
        active,
        manifest,
    ):
        raise PlanAuditRequiredError("plan-audited inputs changed after review")


def build_plan_review_bundle(root: Path, experiment_id: str) -> Path:
    state, manifest = require_active(root, experiment_id, {"PLANNED"})
    if state.get("next_action", {}).get("mode") != "audit_experiment_plan":
        raise ValueError("next action is not audit_experiment_plan")

    active = root / "experiments/active" / experiment_id
    config_path = root / manifest["config"]
    record = (active / "EXPERIMENT.md").read_text(encoding="utf-8")
    validate_plan(record, stage=manifest.get("stage"))
    require_comparison_budget(read_json(config_path), state)
    delta = require_locked_implementation_delta(root, active, manifest)
    inputs = plan_audit_input_hashes(root, active, manifest)
    if plan_hash(
        active / "EXPERIMENT.md",
        config_path,
        active / "SCOPE.json",
    ) != manifest.get("plan_sha256"):
        raise ValueError("locked plan, config, or scope changed")
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")

    request = {
        "schema_version": "1.0",
        **({"novelty_contract_version": manifest["novelty_contract_version"]}
           if novelty_contract_required(manifest) else {}),
        "experiment_id": experiment_id,
        "review_question": (
            "Does the advance go beyond closest work, separating source facts from inference? "
            "Do rival predictions, test and advance criterion match the locked plan? "
            "Could the metric improve without the claim? Are controls, evidence and scale "
            "sufficient for this study role and research goal without trivial fragmentation "
            "or unjustified expansion?"
        ),
        "goal": (root / "research/GOAL.md").read_text(encoding="utf-8"),
        "novelty": latest_novelty(root, experiment_id),
        "locked_plan": plan_record_material(record),
        "config": _auditable_config(read_json(config_path)),
        "training_control_policy": _training_control_policy(root),
        "scope": read_json(active / "SCOPE.json"),
        "implementation_delta": compact_implementation_delta(delta),
        "baseline": _baseline_payload(root, manifest.get("baseline_id")),
        "verdicts": ["pass", "warn", "fail"],
        "rules": {
            "one_primary_metric": True,
            "maximum_diagnostic_guardrails": 1,
            "guardrail_is_not_a_promotion_metric": True,
        },
        "audited_input_hashes": inputs,
        "instruction": (
            "Review only this request. Do not inspect code, data, papers, "
            "results, or repository files outside the bundle."
        ),
    }
    template = (
        root / "experiments/templates/PLAN_AUDIT.md"
    ).read_text(encoding="utf-8").replace("{{EXPERIMENT_ID}}", experiment_id)
    maximum = int(state["budgets"].get("max_plan_audit_chars", 9000))
    serialized = bounded_audit_request(request, template, maximum)

    bundle = root / "review/bundles" / f"{experiment_id}-plan"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    atomic_write_text(bundle / "PLAN_AUDIT_REQUEST.json", serialized)
    atomic_write_text(bundle / "PLAN_AUDIT.md", template)
    return bundle


def _execute() -> str:
    parser = QuietArgumentParser(description="Build one plan audit bundle.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    args = parser.parse_args()
    root = root_from_script()
    return build_plan_review_bundle(
        root,
        args.experiment_id,
    ).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("build-plan-review-bundle", _execute))
