from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_cli_error_is_one_line() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dl_research.cli.sanity",
            "--config",
            "missing.json",
        ],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith("ERROR sanity:")
    assert completed.stderr.count("\n") == 1
