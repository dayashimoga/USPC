"""Migration export and import command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger
from cloudctl.core.migration import MigrationManager
from cloudctl.core.storage import StorageManager

logger = get_logger("cmd.migrate")


def execute_migrate(args: argparse.Namespace) -> int:
    """Run migration export or import."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    storage_mgr = StorageManager(
        data_path=config["storage"]["data_path"],
        config_path=config["storage"]["config_path"],
    )
    mig_mgr = MigrationManager(config, storage_mgr)

    if args.migrate_action == "export":
        out_path = mig_mgr.export_bundle(args.output)
        logger.info(f"Migration bundle exported to: {out_path}")
        return 0
    elif args.migrate_action == "import":
        success = mig_mgr.import_bundle(args.input)
        return 0 if success else 1
    return 1
