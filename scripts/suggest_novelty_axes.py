from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import QuietArgumentParser, root_from_script, run_script

AXIS_TERMS = {
    "mechanism": [
        "mechanism",
        "causal",
        "interaction",
        "inductive bias",
        "architecture",
        "module",
    ],
    "condition": ["condition", "setting", "regime", "constraint", "assumption"],
    "data_regime": ["data", "low-resource", "noisy", "shift", "imbalance", "split"],
    "objective": ["loss", "metric", "objective", "optimization", "calibration"],
    "efficiency": ["compute", "memory", "latency", "sample efficiency", "throughput"],
    "robustness": ["robust", "stability", "generalization", "distribution shift"],
    "failure_mode": ["failure", "limitation", "degrades", "collapse", "overfit"],
}


def _read_optional(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"text file must be utf-8: {path}") from exc


def _flat_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file())


def _approved_text(root: Path) -> str:
    paths: list[Path] = []
    paths.extend(_flat_files(root / "references/records"))
    paths.extend(_flat_files(root / "baselines/records"))
    paths.append(root / "experiments/DIGEST.md")
    paths.append(root / "research/memory/INSIGHTS.md")
    paths.append(root / "research/memory/DEAD_ENDS.md")
    paths.append(root / "research/memory/OPEN_QUESTIONS.md")
    return "\n".join(_read_optional(path) for path in paths)


def suggest_novelty_axes(root: Path) -> str:
    text = _approved_text(root).lower()
    scores: list[tuple[str, int]] = []
    for axis, terms in AXIS_TERMS.items():
        score = 0
        for term in terms:
            pattern = re.escape(term.lower())
            score += len(re.findall(pattern, text))
        if score:
            scores.append((axis, score))
    ranked = sorted(scores, key=lambda item: (-item[1], item[0]))[:5]
    axes = ",".join(f"{axis}:{score}" for axis, score in ranked)
    return f"count={len(ranked)} axes={axes or 'none'}"


def _execute() -> str:
    QuietArgumentParser(
        description="Suggest candidate novelty axes from approved compact records."
    ).parse_args()
    return suggest_novelty_axes(root_from_script())


if __name__ == "__main__":
    raise SystemExit(run_script("suggest-novelty-axes", _execute))
