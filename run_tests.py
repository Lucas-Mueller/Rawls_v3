"""Thin pytest wrapper for historical compatibility."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).parent
MODE_HELP = (
    "Preset test selection. Maps to pytest markers: "
    "ultra_fast -> unit+fast, dev -> unit+component, "
    "ci -> unit+component+integration, full -> all suites including live."
)


def _normalise_pytest_args(extra_args: Sequence[str]) -> list[str]:
    """Strip a leading '--' if present from argparse.REMAINDER."""
    if not extra_args:
        return []
    if extra_args[0] == "--":
        return list(extra_args[1:])
    return list(extra_args)


def build_command(mode: str | None, coverage: bool, extra_args: Sequence[str]) -> list[str]:
    """Construct the pytest command with optional mode and coverage flags."""
    cmd: list[str] = [sys.executable, "-m", "pytest"]
    if mode:
        cmd.append(f"--mode={mode}")
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    cmd.extend(_normalise_pytest_args(extra_args))
    return cmd


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest with optional suite presets.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--mode",
        choices=("ultra_fast", "dev", "ci", "full"),
        help=MODE_HELP,
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enable coverage reporting via pytest-cov.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded directly to pytest.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    cmd = build_command(args.mode, args.coverage, args.pytest_args)
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
