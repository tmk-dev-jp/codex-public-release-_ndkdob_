"""Human-operated Codex boundary configuration; never call from skills or hooks."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.common import QuietArgumentParser, run_script, sha256_bytes as digest  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

PROFILE = "manual-agent-boundary"
BACKUP = "agent-boundary-backup.json"
MARKER = "# Managed by scripts/set_agent_boundary.py"
PROTECTED = (".git", ".codex", ".agents")
PROBE = """
import pathlib, sys
with pathlib.Path(sys.argv[1]).open("rb") as stream:
    stream.read(1)
try:
    with pathlib.Path(sys.argv[2]).open("rb") as stream:
        stream.read(1)
except (PermissionError, FileNotFoundError):
    sys.stdout.write("boundary-ok\\n")
else:
    raise SystemExit("blocked probe was readable")
"""


def parse_toml(value: bytes) -> dict:
    if tomllib is None:
        raise ValueError("Python 3.11 or newer is required")
    return tomllib.loads(value.decode("utf-8"))


def checked_path(value: str | Path, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    if any(char in str(path) for char in "*?[]"):
        raise ValueError("use exact paths, not globs")
    # Reject redirected policy inputs instead of silently granting their targets.
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError(f"symlink path is not supported: {path}")
    path = path.resolve(strict=True)
    if path == Path(path.anchor):
        raise ValueError("a filesystem root cannot be an allowed or denied path")
    return path


def executable(value: str) -> Path:
    found = shutil.which(value)
    if not found:
        raise ValueError(f"Codex executable not found: {value}")
    return Path(found).resolve(strict=True)


def settings_paths(root: Path) -> tuple[Path, Path]:
    folder = root / ".codex"
    config, backup = folder / "config.toml", folder / BACKUP
    for path in (folder, config, backup):
        if path.is_symlink():
            raise ValueError(f"refusing redirected configuration: {path}")
    return config, backup


def make_profile(root: Path, reads: list[str], writes: list[str],
                 denies: list[str], binary: Path) -> dict:
    if not reads and not writes:
        raise ValueError("specify at least one --read or --write path")
    rules = {}
    for values, access in ((reads, "read"), (writes, "write"), (denies, "deny")):
        for value in values:
            path = checked_path(value, root)
            key = str(path)
            if key in rules and rules[key] != access:
                raise ValueError(f"conflicting access rules: {path}")
            rules[key] = access
    allowed = [Path(p) for p, access in rules.items() if access != "deny"]
    denied = [Path(p) for p, access in rules.items() if access == "deny"]
    if any(path.is_relative_to(blocked) for path in allowed for blocked in denied):
        raise ValueError("an allow rule cannot reopen an explicitly denied path")
    if any(binary.is_relative_to(path) for path in denied):
        raise ValueError("a deny rule would block the Codex executable")
    for value in writes:
        path = checked_path(value, root)
        if not path.is_dir():
            raise ValueError("--write requires an existing directory")
        for name in PROTECTED:
            reserved = root / name
            if path.is_relative_to(reserved):
                raise ValueError(f"configuration and control directories stay read-only: {path}")
            if reserved.is_relative_to(path) and str(reserved) not in rules:
                rules[str(reserved)] = "read"
    rules.setdefault(str(binary), "read")
    return {
        "filesystem": {":root": "deny", ":minimal": "read", **dict(sorted(rules.items()))},
        "network": {"enabled": False},
    }


def render(original: bytes, profile: dict) -> bytes:
    config = parse_toml(original)
    if MARKER in original.decode("utf-8"):
        raise ValueError("managed configuration has no matching backup")
    for key in ("default_permissions", "approval_policy", "sandbox_mode"):
        if key in config:
            raise ValueError(f"existing {key} needs manual review before installation")
    if PROFILE in config.get("permissions", {}):
        raise ValueError(f"permission profile already exists: {PROFILE}")
    q = json.dumps
    selection = (
        f'{MARKER}\ndefault_permissions = "{PROFILE}"\n'
        'approval_policy = "never"\n\n'
    )
    table = f'\n[permissions.{PROFILE}.filesystem]\n'
    table += "".join(f"{q(path)} = {q(access)}\n"
                     for path, access in profile["filesystem"].items())
    table += f'\n[permissions.{PROFILE}.network]\nenabled = false\n'
    result = selection.encode() + original + b"\n" + table.encode()
    parse_toml(result)
    return result


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".boundary-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_snapshot(root: Path) -> tuple[bytes, dict | None]:
    config, backup = settings_paths(root)
    current = config.read_bytes() if config.exists() else b""
    if not backup.exists():
        return current, None
    record = json.loads(backup.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("backup must be a JSON object")
    if record.get("schema_version") != 1 or record.get("root") != str(root):
        raise ValueError("backup schema or project path does not match")
    if (not isinstance(record.get("original"), str)
            or not isinstance(record.get("original_existed"), bool)
            or not isinstance(record.get("applied_sha256"), str)):
        raise ValueError("backup fields are invalid")
    original = record["original"].encode("utf-8")
    if digest(original) != record["original_sha256"]:
        raise ValueError("backup content hash does not match")
    if digest(current) not in (record["applied_sha256"], record["original_sha256"],
                               record.get("previous_sha256")):
        raise ValueError("config changed after installation; preserve it and reconcile manually")
    return current, record


def configure(root: Path, profile: dict, apply: bool) -> dict:
    config, backup = settings_paths(root)
    current, record = load_snapshot(root)
    original = record["original"].encode("utf-8") if record else current
    candidate = render(original, profile)
    result = {"profile": PROFILE, "config": str(config), "permissions": profile,
              "state": "planned", "restart_required": False}
    if not apply:
        return result
    if candidate == current:
        result["state"] = "unchanged"
        return result
    snapshot = {
        "schema_version": 1, "root": str(root),
        "original": original.decode("utf-8"),
        "original_existed": record["original_existed"] if record else config.exists(),
        "original_sha256": digest(original), "applied_sha256": digest(candidate),
        "previous_sha256": digest(current),
    }
    # Persist recovery data before replacing the live project configuration.
    atomic_write(backup, (json.dumps(snapshot, ensure_ascii=True, indent=2) + "\n").encode())
    atomic_write(config, candidate)
    result.update(state="configured", restart_required=True)
    return result


def restore(root: Path) -> dict:
    config, backup = settings_paths(root)
    _, record = load_snapshot(root)
    if record is None:
        raise ValueError("no boundary backup exists")
    if record["original_existed"]:
        atomic_write(config, record["original"].encode("utf-8"))
    else:
        config.unlink(missing_ok=True)
    backup.unlink()
    return {"state": "restored", "restart_required": True}


def status(root: Path) -> dict:
    current, record = load_snapshot(root)
    if record is None:
        return {"state": "not_configured"}
    config = parse_toml(current)
    active = (config.get("default_permissions") == PROFILE
              and digest(current) == record["applied_sha256"])
    return {"state": "configured" if active else "pending",
            "profile": PROFILE, "permissions": config.get("permissions", {}).get(PROFILE),
            "live_session_verified": False}


def verify(root: Path, binary: Path, readable: str, blocked_dir: str) -> dict:
    current, record = load_snapshot(root)
    if (record is None or digest(current) != record["applied_sha256"]
            or parse_toml(current).get("default_permissions") != PROFILE):
        raise ValueError("apply a boundary before verification")
    visible = checked_path(readable, root)
    blocked = checked_path(blocked_dir, root)
    if not visible.is_file() or not blocked.is_dir():
        raise ValueError("--readable must be a file and --blocked-dir a directory")
    # Only this disposable probe is read outside the intended boundary.
    with tempfile.TemporaryDirectory(prefix=".agent-boundary-probe-", dir=blocked) as tmp:
        probe = Path(tmp) / "blocked.txt"
        probe.write_text("boundary-probe", encoding="utf-8")
        result = subprocess.run(
            [str(binary), "sandbox", "--permission-profile", PROFILE,
             "--include-managed-config", "-C", str(root), "--",
             sys.executable, "-I", "-S", "-c", PROBE, str(visible), str(probe)],
            capture_output=True, text=True, timeout=30, check=False,
        )
    if result.returncode or result.stdout.strip() != "boundary-ok":
        detail = " ".join((result.stderr or result.stdout).split())[:400]
        raise ValueError(f"sandbox boundary verification failed: {detail or result.returncode}")
    return {"state": "probe_passed", "readable": str(visible), "blocked_directory": str(blocked)}


def run(argv: list[str] | None = None) -> str:
    parser = QuietArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply", "status", "verify", "restore"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--read", action="append", default=[])
    parser.add_argument("--write", action="append", default=[])
    parser.add_argument("--deny", action="append", default=[])
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--readable")
    parser.add_argument("--blocked-dir")
    args = parser.parse_args(argv)
    if tomllib is None:
        raise ValueError("Python 3.11 or newer is required")
    if args.action not in ("plan", "apply") and (args.read or args.write or args.deny):
        raise ValueError("--read, --write, and --deny are only for plan/apply")
    if args.action != "verify" and (args.readable or args.blocked_dir):
        raise ValueError("--readable and --blocked-dir are only for verify")
    root = checked_path(args.root, Path.cwd())
    if not root.is_dir():
        raise ValueError("--root must be a directory")
    if args.action in ("plan", "apply"):
        binary = executable(args.codex)
        profile = make_profile(root, args.read, args.write, args.deny, binary)
        result = configure(root, profile, args.action == "apply")
    elif args.action == "verify":
        if not args.readable or not args.blocked_dir:
            raise ValueError("verify requires --readable and --blocked-dir")
        result = verify(root, executable(args.codex), args.readable, args.blocked_dir)
    elif args.action == "restore":
        result = restore(root)
    else:
        result = status(root)
    # The shared one-line adapter collapses whitespace; preserve spaces inside JSON paths.
    return json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace(
        " ", "\\u0020"
    )


def main(argv: list[str] | None = None) -> int:
    return run_script("agent-boundary", lambda: run(argv))

if __name__ == "__main__":
    raise SystemExit(main())
