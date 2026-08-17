"""Comprehensive tests for shell execution and command helpers."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from cloudctl.utils.shell import run_command


def test_run_command_basic_and_env():
    # Successful execution
    res = run_command(["python", "-c", "print('hello_uspc_shell')"])
    assert res.success
    assert "hello_uspc_shell" in res.stdout

    # Failure with non-zero exit code
    res_fail = run_command(["python", "-c", "import sys; sys.exit(42)"])
    assert not res_fail.success
    assert res_fail.returncode == 42


def test_run_command_timeout():
    # Test subprocess TimeoutExpired
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["sleep", "10"], timeout=0.1)
    ):
        res = run_command(["sleep", "10"], timeout=0.1)
        assert not res.success
        assert res.returncode == -1
        assert "timed out" in res.stderr.lower()


def test_run_command_not_found_and_exceptions():
    with patch("subprocess.run", side_effect=FileNotFoundError("Executable not found")):
        res = run_command(["non_existent_binary_xyz_123"])
        assert not res.success
        assert res.returncode == -1
        assert "Executable not found" in res.stderr

    with patch("subprocess.run", side_effect=Exception("Generic OS failure")):
        res2 = run_command(["any_cmd"])
        assert not res2.success
        assert res2.returncode == -1
        assert "Generic OS failure" in res2.stderr
