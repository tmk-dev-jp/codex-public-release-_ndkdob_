from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dl_research.experiment.runner import ExperimentRunner
from scripts.build_context import build_context
from scripts.build_decision_facts import build_decision_facts
from scripts.build_implementation_review_bundle import (
    ImplementationAuditRequiredError,
    require_accepted_implementation_audit,
)
from scripts.build_plan_review_bundle import (
    PlanAuditRequiredError,
    require_accepted_plan_audit,
)
from scripts.build_review_bundle import build_review_bundle
from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    one_line,
    read_json,
    root_from_script,
    sha256_file,
    sha256_path_set,
)
from scripts.implementation_delta import require_current_implementation_delta
from scripts.records import plan_hash
from scripts.workflow import (
    mark_failed,
    require_active,
    set_phase,
)


def _update_index(root: Path, experiment_id: str, phase: str) -> None:
    path = root / "experiments/INDEX.json"
    payload = read_json(path)
    for item in payload.get("experiments", []):
        if item.get("id") == experiment_id:
            item["phase"] = phase
    atomic_write_json(path, payload)


def execute_experiment(root: Path, experiment_id: str) -> str:
    state, manifest = require_active(
        root,
        experiment_id,
        {"IMPLEMENTED", "SANITY_PASSED", "TRAINED"},
    )
    active = root / "experiments/active" / experiment_id
    config_path = root / manifest["config"]
    record_path = active / "EXPERIMENT.md"
    scope_path = active / "SCOPE.json"
    if sha256_file(config_path) != manifest.get("locked_config_sha256"):
        raise ValueError("config changed after plan locking")
    if plan_hash(record_path, config_path, scope_path) != manifest.get("plan_sha256"):
        raise ValueError("locked plan, config, or scope changed")
    current_implementation = sha256_path_set(root, manifest.get("implementation_files", []))
    if current_implementation != manifest.get("implementation_sha256"):
        raise ValueError("implementation changed after mark-implemented")
    require_current_implementation_delta(root, active, manifest)
    require_accepted_plan_audit(root, active, manifest, allow_warn=True)
    require_accepted_implementation_audit(root, state, active, manifest)

    runner = ExperimentRunner.from_path(config_path, root=root)
    result_dir = root / manifest["result_dir"]
    runner._prepare_output_dir()
    error_path = result_dir / "error.json"
    if error_path.exists():
        error_path.unlink()

    phase = state.get("phase")
    if phase == "IMPLEMENTED":
        sanity = runner.sanity()
        atomic_write_json(result_dir / "sanity.json", sanity)
        set_phase(
            root,
            experiment_id,
            "SANITY_PASSED",
            objective="Run the bounded training and aggregate test evaluation.",
            review_required=False,
        )
    elif phase == "SANITY_PASSED" and not (result_dir / "sanity.json").is_file():
        raise FileNotFoundError("sanity artifact is missing for SANITY_PASSED resume")

    if phase in {"IMPLEMENTED", "SANITY_PASSED"}:
        metrics = runner.cycle()
        runtime_manifest_path = result_dir / "manifest.json"
        runtime_manifest = read_json(runtime_manifest_path)
        runtime_manifest.update(
            {
                "plan_sha256": manifest.get("plan_sha256"),
                "plan_audit": manifest.get("plan_audit"),
                "implementation_sha256": manifest.get("implementation_sha256"),
                "implementation_files": manifest.get("implementation_files", []),
                "implementation_delta": manifest.get("implementation_delta"),
                "implementation_audit": manifest.get("implementation_audit"),
            }
        )
        atomic_write_json(runtime_manifest_path, runtime_manifest)
        set_phase(
            root,
            experiment_id,
            "TRAINED",
            objective="Evaluate aggregate evidence against the locked decision rule.",
            review_required=False,
        )
    else:
        metrics_path = result_dir / "metrics.json"
        if not metrics_path.is_file() or not (result_dir / "manifest.json").is_file():
            raise FileNotFoundError("trained aggregate artifacts are missing")
        metrics = read_json(metrics_path)

    review_mode = str(runner.config.experiment.review_mode)
    if metrics.get("review_mode") != review_mode:
        raise ValueError("metrics review mode does not match the locked config")
    if review_mode == "independent":
        build_review_bundle(root, experiment_id)
        set_phase(
            root,
            experiment_id,
            "REVIEW_REQUIRED",
            objective=(
                "Use the read-only evaluator on the compact review bundle, then accept its "
                "evaluation."
            ),
            review_required=True,
        )
        final_phase = "REVIEW_REQUIRED"
    else:
        build_decision_facts(root, experiment_id)
        set_phase(
            root,
            experiment_id,
            "READY_TO_FINALIZE",
            objective=(
                "Fill Conclusion and Issues and Next Direction from aggregate metrics, then "
                "finalize."
            ),
            review_required=False,
        )
        final_phase = "READY_TO_FINALIZE"

    _update_index(root, experiment_id, final_phase)
    build_context(root)
    metric = metrics["primary_metric"]
    return f"{experiment_id} phase={final_phase} {metric['name']}={metric['value']:.6f}"


def main() -> int:
    parser = QuietArgumentParser(description="Run sanity, training, and aggregate evaluation once.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    try:
        args = parser.parse_args()
        root = root_from_script()
        detail = execute_experiment(root, args.experiment_id)
        print(f"OK run-experiment {one_line(detail)}")
        return 0
    except Exception as exc:
        experiment_id = getattr(locals().get("args", None), "experiment_id", None)
        root = locals().get("root", root_from_script())
        if experiment_id and not isinstance(
            exc,
            (PlanAuditRequiredError, ImplementationAuditRequiredError),
        ):
            try:
                active_manifest = root / "experiments/active" / experiment_id / "MANIFEST.json"
                if active_manifest.is_file():
                    manifest = read_json(active_manifest)
                    result_dir = root / manifest["result_dir"]
                    comparison_state = result_dir / "comparison_state.json"
                    if comparison_state.is_file():
                        progress = read_json(comparison_state)
                        if progress.get("status") == "running":
                            progress["status"] = "failed"
                            if progress.get("runs") and progress["runs"][-1]["status"] == "running":
                                progress["runs"][-1].update(
                                    {"status": "failed", "error_type": type(exc).__name__}
                                )
                            atomic_write_json(comparison_state, progress)
                    atomic_write_json(
                        result_dir / "error.json",
                        {
                            "schema_version": "1.0",
                            "experiment_id": experiment_id,
                            "phase": read_json(root / "research/STATE.json").get("phase"),
                            "error_type": type(exc).__name__,
                            "message": one_line(exc)[:400],
                        },
                    )
                    mark_failed(
                        root,
                        experiment_id,
                        "Diagnose error.json and apply one minimal repair.",
                    )
                    _update_index(root, experiment_id, "FAILED")
                    build_context(root)
            except Exception:
                pass
        print(
            f"ERROR run-experiment: {type(exc).__name__}: {one_line(exc)[:400]}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
