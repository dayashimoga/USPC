"""Service lifecycle commands: start, stop, restart."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.lifecycle")

SERVICES = ["uspc-postgres", "uspc-redis", "uspc-headscale", "uspc-nextcloud", "uspc-media"]


def execute_start(args: argparse.Namespace) -> int:
    """Start all USPC containers."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    cm = ContainerManager(config["runtime"]["engine"])
    logger.info("Starting all USPC cloud services...")

    success = True
    for svc in SERVICES:
        if svc == "uspc-media" and not config.get("media", {}).get("enabled", True):
            continue
        if cm.start_container(svc):
            logger.info(f"Started container: {svc}")
        else:
            logger.warning(f"Could not start container: {svc}")
            success = False

    return 0 if success else 1


def execute_stop(args: argparse.Namespace) -> int:
    """Stop all USPC containers."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    cm = ContainerManager(config["runtime"]["engine"])
    logger.info("Stopping all USPC cloud services...")

    # Stop in reverse dependency order
    for svc in reversed(SERVICES):
        if cm.stop_container(svc):
            logger.info(f"Stopped container: {svc}")
        else:
            logger.debug(f"Container {svc} was not running or failed to stop")

    return 0


def execute_restart(args: argparse.Namespace) -> int:
    """Restart all USPC containers."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    cm = ContainerManager(config["runtime"]["engine"])
    logger.info("Restarting all USPC cloud services...")

    success = True
    for svc in SERVICES:
        if svc == "uspc-media" and not config.get("media", {}).get("enabled", True):
            continue
        if cm.restart_container(svc):
            logger.info(f"Restarted container: {svc}")
        else:
            logger.warning(f"Could not restart container: {svc}")
            success = False

    return 0 if success else 1
