from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import atomic_write_text, read_json, root_from_script, run_script
from scripts.records import field


def build_digest(root: Path) -> Path:
    state = read_json(root / "research/STATE.json")
    index = read_json(root / "experiments/INDEX.json")
    maximum = int(state["budgets"].get("max_completed_digest_rows", 20))
    completed = [
        item for item in index.get("experiments", []) if item.get("status") == "completed"
    ][-maximum:]
    lines = [
        "# Completed Experiment Digest",
        "",
        "| ID | Stage | Decision | Rule assessment | Primary result | Next action |",
        "|---|---|---|---|---|---|",
    ]
    for item in completed:
        record_path = root / item["record"]
        text = record_path.read_text(encoding="utf-8") if record_path.is_file() else ""
        values = [
            str(item["id"]),
            str(item.get("stage", "unknown")),
            field(text, "Decision") if text else "unknown",
            field(text, "Decision-rule assessment") if text else "unknown",
            field(text, "Primary result") if text else "unknown",
            field(text, "Next action") if text else "unknown",
        ]
        clean = [value.replace("|", "/").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(clean) + " |")
    aborted = [item for item in index.get("experiments", []) if item.get("status") == "aborted"]
    if aborted:
        lines.extend([
            "", "## Aborted Comparisons", "",
            "Closed without scientific evaluation; retained results are not accepted evidence.",
            "", "| ID | Stage | Abort reason |", "|---|---|---|",
        ])
        for item in aborted[-min(maximum, 5):]:
            reason = item["abort_reason"]
            summary = reason if len(reason) <= 160 else reason[:157] + "..."
            values = [item["id"], item.get("stage", "unknown"), summary]
            clean = [str(value).replace("|", "/").replace("\n", " ") for value in values]
            lines.append("| " + " | ".join(clean) + " |")
    path = root / "experiments/DIGEST.md"
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def _execute() -> str:
    root = root_from_script()
    return build_digest(root).relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(run_script("build-digest", _execute))
