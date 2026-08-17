"""Initialize USPC configuration and secure secrets."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.detect import detect_host
from cloudctl.core.logging import get_logger
from cloudctl.core.secrets import SecretManager

logger = get_logger("cmd.init")


def execute_init(args: argparse.Namespace) -> int:
    """Execute the 'cloudctl init' command."""
    logger.info("Initializing Universal Personal Cloud Platform (USPC)...")

    host_info = detect_host()
    logger.info(
        f"Detected Platform: {host_info.os_name} ({host_info.arch}) | RAM: {host_info.total_ram_gb} GB | Engine: {host_info.container_engine}"
    )

    cfg_mgr = ConfigManager(config_path=args.config if hasattr(args, "config") else None)

    # Check if config file exists
    if cfg_mgr.config_path.exists() and not getattr(args, "force", False):
        logger.warning(f"Configuration file already exists at {cfg_mgr.config_path}")
        logger.info("Use --force to overwrite existing configuration.")
    else:
        # Load defaults and adapt to host
        config_data = cfg_mgr.load_defaults()

        if getattr(args, "name", None):
            config_data["cloud"]["name"] = args.name
        if getattr(args, "domain", None):
            config_data["cloud"]["domain"] = args.domain

        # If engine was explicitly specified
        if host_info.container_engine != "none":
            config_data["runtime"]["engine"] = host_info.container_engine

        # Save config
        cfg_mgr.save_config(config_data)
        logger.info(f"Created configuration file: {cfg_mgr.config_path}")

    # Generate initial credentials
    secret_mgr = SecretManager()
    secret_mgr.load_or_generate_secrets()
    logger.info("Generated cryptographic keys and credentials securely in ~/.uspc/secrets/")

    print("\n" + "=" * 60)
    print(" USPC Initialization Complete!")
    print("=" * 60)
    print(f" * Config file : {cfg_mgr.config_path}")
    print(f" * Secrets dir : {secret_mgr.secrets_dir}")
    print(f" * Detected OS : {host_info.os_name} ({host_info.arch})")
    print(f" * Container   : {host_info.container_engine} (v{host_info.engine_version})")
    print("\nNext step: Run './cloudctl install' to start deployment.")
    print("=" * 60 + "\n")
    return 0
