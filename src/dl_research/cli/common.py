"""One-line CLI output helpers."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any


class QuietArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        raise ValueError(message)


def one_line(value: object) -> str:
    return " ".join(str(value).split())


def run_cli(name: str, action: Callable[[], str]) -> int:
    try:
        detail = one_line(action())
        print(f"OK {name} {detail}".rstrip())
        return 0
    except Exception as exc:
        message = one_line(exc)[:400]
        print(f"ERROR {name}: {type(exc).__name__}: {message}", file=sys.stderr)
        return 1


def config_parser(description: str) -> QuietArgumentParser:
    parser = QuietArgumentParser(description=description)
    parser.add_argument("--config", required=True)
    return parser
