"""Backup command."""

from __future__ import annotations

import argparse

from cloudctl.core.backup import BackupManager
from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.backup")


def execute_backup(args: argparse.Namespace) -> int:
    """Run encrypted Restic backup."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    bm = BackupManager(config)

    if getattr(args, "verify", False):
        return 0 if bm.verify_repository() else 1

    tag = getattr(args, "tag", "manual")
    success = bm.create_backup(tag=tag, verify_after=True)
    return 0 if success else 1
