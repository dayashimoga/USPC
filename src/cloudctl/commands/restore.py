"""Restore command."""

from __future__ import annotations

import argparse

from cloudctl.core.backup import BackupManager
from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.restore")


def execute_restore(args: argparse.Namespace) -> int:
    """Run restore from encrypted backup snapshot."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    bm = BackupManager(config)

    if getattr(args, "test", False):
        return 0 if bm.test_restore_isolation() else 1

    snapshot = getattr(args, "snapshot", "latest")
    dry_run = getattr(args, "dry_run", False)
    success = bm.restore_backup(snapshot_id=snapshot, dry_run=dry_run)
    return 0 if success else 1
