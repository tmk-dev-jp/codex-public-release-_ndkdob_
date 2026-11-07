#!/usr/bin/env python3
"""Advisory stop hook with one-line JSON output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / "research/STATE.json").is_file():
            return candidate
    raise FileNotFoundError("repository root not found")


def main() -> int:
    try:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        root = _root(Path(payload.get("cwd") or ".").resolve())
        build = subprocess.run(
            [sys.executable, str(root / "scripts/build_context.py")],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        check = subprocess.run(
            [sys.executable, str(root / "scripts/validate.py"), "--json"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        messages: list[str] = []
        if build.returncode != 0:
            messages.append((build.stderr or build.stdout).strip()[:400])
        try:
            validation = json.loads(check.stdout)
        except Exception:
            validation = {
                "ok": False,
                "errors": [(check.stderr or check.stdout or "validation failed")[:600]],
            }
        if not validation.get("ok"):
            messages.append("Validation: " + "; ".join(validation.get("errors", []))[:800])
        response: dict[str, object] = {"continue": True}
        if messages:
            response["systemMessage"] = " ".join(messages)
        print(json.dumps(response, separators=(",", ":")))
    except Exception as exc:
        print(
            json.dumps(
                {"continue": True, "systemMessage": f"Validation hook failed: {exc}"},
                separators=(",", ":"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
