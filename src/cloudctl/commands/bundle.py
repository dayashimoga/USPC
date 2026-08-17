"""Offline bundle creation command."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

from cloudctl.core.config import get_repo_root
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.bundle")


def execute_bundle(args: argparse.Namespace) -> int:
    """Create self-contained offline deployment bundle."""
    repo_root = get_repo_root()
    out_file = Path(args.output).expanduser().resolve()
    logger.info(f"Creating USPC offline installation bundle at '{out_file}'...")

    exclude_patterns = [
        "__pycache__",
        ".git",
        ".venv",
        "data",
        "backups",
        ".pytest_cache",
        "media_cache",
        "*.pyc",
    ]

    def filter_func(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        for pat in exclude_patterns:
            if pat in tarinfo.name:
                return None
        return tarinfo

    with tarfile.open(out_file, "w:gz") as tar:
        tar.add(repo_root, arcname="uspc", filter=filter_func)

    logger.info(f"Offline bundle created successfully: {out_file}")
    return 0
