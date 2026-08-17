"""Safe shell execution utilities with timeouts and secret masking."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of shell command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def mask_secrets(text: str, secrets_to_mask: Sequence[str] | None = None) -> str:
    """Mask known sensitive strings in command outputs."""
    if not text or not secrets_to_mask:
        return text
    masked = text
    for secret in secrets_to_mask:
        if secret and len(secret) > 3 and secret in masked:
            masked = masked.replace(secret, "********")
    return masked


def run_command(
    cmd: Sequence[str] | str,
    cwd: str | None = None,
    timeout: float = 120.0,
    env: dict[str, str] | None = None,
    secrets: Sequence[str] | None = None,
    check: bool = False,
    shell: bool = False,
) -> CommandResult:
    """Execute command safely and capture structured output."""
    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            env=merged_env,
            shell=shell,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout = mask_secrets(proc.stdout, secrets)
        stderr = mask_secrets(proc.stderr, secrets)

        result = CommandResult(
            command=mask_secrets(cmd_str, secrets),
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        raw_out = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        raw_err = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        result = CommandResult(
            command=mask_secrets(cmd_str, secrets),
            returncode=-1,
            stdout=mask_secrets(raw_out, secrets),
            stderr=mask_secrets(raw_err, secrets)
            + f"\n[ERROR] Command timed out after {timeout} seconds",
            timed_out=True,
        )
    except Exception as exc:
        result = CommandResult(
            command=mask_secrets(cmd_str, secrets),
            returncode=-1,
            stdout="",
            stderr=f"[ERROR] Failed to launch command: {exc}",
            timed_out=False,
        )

    if check and not result.success:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {result.command}\n"
            f"Stderr: {result.stderr}\nStdout: {result.stdout}"
        )

    return result
