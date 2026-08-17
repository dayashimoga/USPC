"""Test command runner."""

from __future__ import annotations

import argparse
import sys

from cloudctl.utils.shell import run_command


def execute_test(args: argparse.Namespace) -> int:
    """Run pytest suite."""
    cmd = [sys.executable, "-m", "pytest"]
    if getattr(args, "media_only", False):
        cmd.append("tests/media/")
    else:
        cmd.append("tests/")

    if getattr(args, "coverage", False):
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    print(f"Running test suite: {' '.join(cmd)}")
    res = run_command(cmd, timeout=300.0)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
    return res.returncode
