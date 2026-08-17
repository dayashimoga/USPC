"""Uninstall command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import remove_path_safely

logger = get_logger("cmd.uninstall")

SERVICES = ["uspc-postgres", "uspc-redis", "uspc-headscale", "uspc-nextcloud", "uspc-media"]


def execute_uninstall(args: argparse.Namespace) -> int:
    """Safely stop and remove all USPC containers and optionally purge storage."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    cm = ContainerManager(config["runtime"]["engine"])

    logger.info("Uninstalling USPC containers and networks...")
    for svc in SERVICES:
        cm.remove_container(svc, force=True)
        logger.info(f"Removed container: {svc}")

    if getattr(args, "purge_data", False):
        if not getattr(args, "force", False):
            print(
                "\n[WARNING] --purge-data will permanently delete all cloud files and database storage!"
            )
            confirm = input("Are you sure you want to delete all data? (yes/no): ")
            if confirm.lower() != "yes":
                logger.info("Aborting storage purge.")
                return 0

        logger.info("Purging persistent storage directories...")
        remove_path_safely(config["storage"]["data_path"])
        remove_path_safely(config["storage"]["config_path"])
        logger.info("Persistent storage purged.")

    logger.info("USPC uninstallation complete.")
    return 0
