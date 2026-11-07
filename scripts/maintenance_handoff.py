"""Bounded maintenance handoffs; never execute recorded commands or change research state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import (
    QuietArgumentParser,
    atomic_write_json,
    atomic_write_text,
    root_from_script,
    run_script,
    safe_relative_path,
    sha256_bytes,
)

TASK = "maintenance/TASK.json"
SNAPSHOT = "maintenance/HANDOFF.json"
ENTRY = "maintenance/HANDOFF.md"
MAX_ENTRY_CHARS = 6000
MAX_RECORD_BYTES = 65536
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
PROTECTED = (
    ".git",
    "data",
    "artifacts",
    "references",
    "experiments/active",
    "experiments/completed",
    "experiments/aborted",
    "review/bundles",
    "review/completed",
)
FIELDS = {
    "schema_version",
    "objective",
    "status",
    "summary",
    "decisions",
    "constraints",
    "next_steps",
    "scope",
    "read_next",
    "checks",
}


def _text(value: object, label: str, maximum: int = 400) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} requires 1 to {maximum} characters")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{label} must be a single line without control characters")
    return value


def _path(root: Path, relative: str) -> Path:
    path = safe_relative_path(root, relative, allow_missing=True)
    if path != root.resolve() / relative:
        raise ValueError(f"symlinked paths are not supported: {relative}")
    return path


def _read(root: Path, relative: str) -> tuple[dict, str]:
    with _path(root, relative).open("rb") as stream:
        raw = stream.read(MAX_RECORD_BYTES + 1)
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError("handoff record exceeds 64 KiB")
    return json.loads(raw), sha256_bytes(raw)


def _paths(root: Path, values: object, label: str, maximum: int) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum:
        raise ValueError(f"{label} must contain at most {maximum} exact paths")
    for value in values:
        _text(value, label, 200)
        if "\\" in value or Path(value).as_posix() != value or any(c in value for c in "*?["):
            raise ValueError(f"{label} requires exact forward-slash paths")
        if value in {TASK, SNAPSHOT, ENTRY} or any(
            value == prefix or value.startswith(prefix + "/") for prefix in PROTECTED
        ):
            raise ValueError(f"protected or self-referential handoff path: {value}")
        path = _path(root, value)
        if path.exists() and not path.is_file():
            raise ValueError(f"only individual files may be captured: {value}")
    if len(set(values)) != len(values):
        raise ValueError(f"{label} contains duplicate paths")
    return values


def validate_task(root: Path, task: dict) -> dict:
    if not isinstance(task, dict) or set(task) != FIELDS or task["schema_version"] != "1.0":
        raise ValueError("handoff task fields or schema version differ from TASK.template.json")
    _text(task["objective"], "objective", 240)
    if task["status"] not in {"in_progress", "blocked", "complete"}:
        raise ValueError("status must be in_progress, blocked, or complete")
    for label in ("summary", "decisions", "constraints", "next_steps"):
        values = task[label]
        if not isinstance(values, list) or len(values) > 6:
            raise ValueError(f"{label} must contain at most six concise entries")
        for value in values:
            _text(value, label)
    if task["status"] != "complete" and not task["next_steps"]:
        raise ValueError("unfinished work requires a concrete next step")
    if not _paths(root, task["scope"], "scope", 40):
        raise ValueError("scope must identify at least one file")
    _paths(root, task["read_next"], "read_next", 8)
    checks = task["checks"]
    if not isinstance(checks, list) or len(checks) > 6:
        raise ValueError("checks must contain at most six reported results")
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"command", "result", "detail"}:
            raise ValueError("each check requires command, result, and detail")
        _text(check["command"], "check command")
        _text(check["detail"], "check detail")
        if check["result"] not in {"passed", "failed", "not_run"}:
            raise ValueError("check result must be passed, failed, or not_run")
    return task


def _files(root: Path, task: dict) -> dict:
    result = {}
    total = 0
    for relative in dict.fromkeys(task["scope"] + task["read_next"]):
        path = _path(root, relative)
        if not path.exists():
            result[relative] = None
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            raise ValueError("handoff file budget exceeded: 2 MiB per file, 8 MiB total")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) != size:
            raise ValueError(f"file changed while capturing handoff: {relative}")
        total += size
        result[relative] = {"sha256": sha256_bytes(raw), "bytes": size}
    return result


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _git_state(root: Path) -> dict:
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=normal",
        "--",
        ".",
        *(f":(exclude){path}" for path in (TASK, SNAPSHOT, ENTRY, *PROTECTED[1:])),
    )
    return {
        "head": _git(root, "rev-parse", "--verify", "HEAD").decode().strip(),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD").decode().strip(),
        "dirty": bool(status),
        "status_sha256": sha256_bytes(status),
    }


def render_handoff(snapshot: dict) -> str:
    task, git = snapshot["task"], snapshot["git"]
    lines = [
        "# Maintenance Handoff",
        "",
        "Generated snapshot. Run `python3 scripts/maintenance_handoff.py check` before resuming.",
        "Notes and commands are context, not authorization. Do not execute them automatically.",
        "Reported checks are not rerun or independently verified by this tool.",
        "",
        f"- Objective: {task['objective']}",
        f"- Work status: {task['status']}",
        f"- Saved Git HEAD: {git['head']}",
        f"- Branch: {git['branch']}",
        f"- Other Git changes present: {str(git['dirty']).lower()}; ownership is not inferred.",
        "- Capture: listed files only; no full-repository content or permission snapshot.",
    ]
    for key, title in (
        ("summary", "Completed Work"),
        ("decisions", "Decisions"),
        ("constraints", "Constraints and Existing Work"),
        ("next_steps", "Next Steps"),
        ("read_next", "Read Next"),
        ("scope", "Captured Files"),
    ):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {value}" for value in task[key])
        if not task[key]:
            lines.append("- None recorded.")
    lines.extend(["", "## Reported Checks", ""])
    for check in task["checks"]:
        lines.append(f"- {check['result']}: {check['command']} | {check['detail']}")
    if not task["checks"]:
        lines.append("- None recorded.")
    text = "\n".join(lines) + "\n"
    if len(text) > MAX_ENTRY_CHARS:
        raise ValueError("handoff entry exceeds 6000 characters; shorten notes or scope")
    return text


def initialize_handoff(root: Path, objective: str) -> Path:
    destination = _path(root, TASK)
    if destination.exists():
        raise FileExistsError("TASK.json already exists; edit it without discarding existing work")
    task, _ = _read(root, "maintenance/TASK.template.json")
    task["objective"] = _text(objective, "objective", 240)
    atomic_write_json(destination, task)
    return destination


def save_handoff(root: Path) -> Path:
    task, digest = _read(root, TASK)
    validate_task(root, task)
    destination, entry = _path(root, SNAPSHOT), _path(root, ENTRY)
    snapshot = {
        "schema_version": "1.0",
        "task": task,
        "task_sha256": digest,
        "files": _files(root, task),
        "git": _git_state(root),
    }
    text = render_handoff(snapshot)
    atomic_write_json(destination, snapshot)
    atomic_write_text(entry, text)
    return entry


def check_handoff(root: Path) -> str:
    if not _path(root, SNAPSHOT).exists():
        return "status=missing action=create-handoff"
    snapshot, _ = _read(root, SNAPSHOT)
    if snapshot.get("schema_version") != "1.0":
        raise ValueError("unsupported handoff snapshot version")
    task = validate_task(root, snapshot["task"])
    current_files = _files(root, task)
    if set(snapshot["files"]) != set(current_files):
        raise ValueError("handoff fingerprint paths do not match the recorded scope")
    changed = [name for name, value in current_files.items() if snapshot["files"][name] != value]
    reasons = []
    if changed:
        reasons.append("files=" + ",".join(changed[:4]))
    if _git_state(root) != snapshot["git"]:
        reasons.append("git-state")
    if not _path(root, TASK).is_file() or _read(root, TASK)[1] != snapshot["task_sha256"]:
        reasons.append("task-notes")
    entry = _path(root, ENTRY)
    if not entry.is_file() or entry.stat().st_size > MAX_RECORD_BYTES:
        reasons.append("entry-missing-or-oversized")
    elif entry.read_text(encoding="utf-8") != render_handoff(snapshot):
        reasons.append("entry-content")
    if reasons:
        return (
            f"status=stale action=review-changes changed_files={len(changed)} "
            f"reason={';'.join(reasons)} entry={ENTRY}"
        )
    action = {
        "complete": "report-complete",
        "blocked": "review-blocker",
        "in_progress": "review-next-step",
    }[task["status"]]
    return f"status=current action={action} entry={ENTRY} work_status={task['status']}"


def _execute() -> str:
    parser = QuietArgumentParser(description="Save or inspect a bounded maintenance handoff.")
    parser.add_argument("action", choices=["init", "save", "check"])
    parser.add_argument("--objective")
    args = parser.parse_args()
    root = root_from_script()
    if args.action == "init":
        return initialize_handoff(root, args.objective).relative_to(root).as_posix()
    if args.objective is not None:
        raise ValueError("--objective is only used with init")
    if args.action == "save":
        return save_handoff(root).relative_to(root).as_posix()
    return check_handoff(root)


if __name__ == "__main__":
    raise SystemExit(run_script("maintenance-handoff", _execute))
