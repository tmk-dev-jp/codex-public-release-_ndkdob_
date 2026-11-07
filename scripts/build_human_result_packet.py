from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_decision_facts import (
    build_decision_facts,
    load_baseline_payload,
)
from scripts.common import (
    QuietArgumentParser,
    atomic_write_text,
    read_json,
    root_from_script,
    run_script,
)
from scripts.workflow import require_active


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _render(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def build_human_result_packet(root: Path, experiment_id: str, *, force: bool = False) -> Path:
    decision_facts_path = build_decision_facts(root, experiment_id)
    _, manifest = require_active(
        root,
        experiment_id,
        {"TRAINED", "REVIEW_REQUIRED", "READY_TO_FINALIZE"},
    )
    active = root / "experiments/active" / experiment_id
    result_dir = root / manifest["result_dir"]
    metrics_path = result_dir / "metrics.json"
    runtime_manifest_path = result_dir / "manifest.json"
    if not metrics_path.is_file() or not runtime_manifest_path.is_file():
        raise FileNotFoundError("aggregate metrics or runtime manifest is missing")

    output = root / "human/results" / experiment_id
    if output.exists() and force:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    interpretation_path = output / "INTERPRETATION.md"
    if interpretation_path.exists() and not force:
        raise FileExistsError("human interpretation file already exists; use --force to overwrite")

    values = {
        "EXPERIMENT_ID": experiment_id,
        "EXPERIMENT_TEXT": (active / "EXPERIMENT.md").read_text(encoding="utf-8"),
        "METRICS_JSON": _json_block(read_json(metrics_path)),
        "MANIFEST_JSON": _json_block(read_json(runtime_manifest_path)),
        "BASELINE_JSON": _json_block(
            load_baseline_payload(root, manifest.get("baseline_id"))
        ),
        "DECISION_FACTS_JSON": _json_block(read_json(decision_facts_path)),
        "PLAN_AUDIT": (active / "PLAN_AUDIT.md").read_text(encoding="utf-8")
        if (active / "PLAN_AUDIT.md").is_file()
        else "Not available for this experiment.",
        "IMPLEMENTATION_AUDIT": (active / "IMPLEMENTATION_AUDIT.md").read_text(encoding="utf-8")
        if (active / "IMPLEMENTATION_AUDIT.md").is_file()
        else "Not available for this experiment.",
        "INTEGRITY_AUDIT": (active / "INTEGRITY_AUDIT.md").read_text(encoding="utf-8")
        if (active / "INTEGRITY_AUDIT.md").is_file()
        else "Not available for this experiment.",
    }
    results_template = (root / "human/templates/HUMAN_RESULTS.md").read_text(encoding="utf-8")
    interpretation_template = (root / "human/templates/HUMAN_INTERPRETATION.md").read_text(
        encoding="utf-8"
    )
    atomic_write_text(output / "RESULTS.md", _render(results_template, values))
    atomic_write_text(interpretation_path, _render(interpretation_template, values))
    return output


def _execute() -> str:
    parser = QuietArgumentParser(description="Build one human-readable result packet.")
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = root_from_script()
    return build_human_result_packet(root, args.experiment_id, force=args.force).relative_to(
        root
    ).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("build-human-result-packet", _execute))
