"""Automated one-command bootstrap and environment setup for USPC (cloudctl setup)."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.detect import detect_host
from cloudctl.core.logging import get_logger
from cloudctl.core.secrets import SecretManager
from cloudctl.core.storage import StorageManager

logger = get_logger("cmd.setup")


def execute_setup(args: argparse.Namespace) -> int:
    """
    Execute full automated one-command setup.
    Performs host discovery, prerequisites check, config initialization,
    and calls install workflow in an idempotent, reboot-safe manner.
    """
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)
    config_path = getattr(args, "config", None)

    logger.info(f"Starting USPC setup bootstrap{' [DRY-RUN]' if dry_run else ''}...")

    # Step 1: Detect Host Environment & Capabilities
    host = detect_host()
    logger.info(
        f"[Setup] Host detected: {host.os_name} {host.os_release} ({host.arch}), "
        f"Cores: {host.cpu_cores}, RAM: {host.total_ram_gb} GB, Engine: {host.container_engine}"
    )

    if not host.is_root_or_admin and host.os_name == "linux" and host.container_engine == "none":
        logger.warning(
            "[Setup] Non-root user without container engine detected. Rootless Podman will be configured."
        )

    # Step 2: Initialize or load configuration
    cfg_mgr = ConfigManager(config_path=config_path)
    if not cfg_mgr.config_path.exists() or force:
        logger.info(f"[Setup] Initializing baseline configuration at {cfg_mgr.config_path}...")
        if not dry_run:
            defaults = cfg_mgr.load_defaults()
            # Customize domain/name if detected or provided
            if getattr(args, "domain", None):
                defaults.setdefault("cloud", {})["domain"] = args.domain
            if getattr(args, "name", None):
                defaults.setdefault("cloud", {})["name"] = args.name
            cfg_mgr.save_config(defaults)
    else:
        logger.info(f"[Setup] Existing configuration found at {cfg_mgr.config_path}")

    config = cfg_mgr.load_config()

    # Step 3: Initialize cryptographic secrets
    secret_mgr = SecretManager()
    if dry_run:
        logger.info("[DRY-RUN] Would generate/verify cryptographic secrets in secure vault.")
    else:
        _ = secret_mgr.load_or_generate_secrets(force=force)
        logger.info(f"[Setup] Secret vault initialized at {secret_mgr.secrets_file} (mode 0600)")

    # Step 4: Validate and prepare storage mounts
    storage_mgr = StorageManager(
        data_path=config["storage"]["data_path"],
        config_path=config["storage"]["config_path"],
        min_free_space_gb=config["storage"]["min_free_space_gb"],
    )
    if dry_run:
        logger.info("[DRY-RUN] Would initialize storage hierarchy and verify partition capacity.")
    else:
        paths = storage_mgr.initialize_storage()
        logger.info(f"[Setup] Storage hierarchy verified at {paths.base_data}")

    # Step 5: Delegate to installation engine
    from cloudctl.commands.install import execute_install

    install_args = argparse.Namespace(
        dry_run=dry_run,
        skip_smoke_test=getattr(args, "skip_smoke_test", False),
        config=config_path,
    )

    rc = execute_install(install_args)

    if rc == 0:
        logger.info("[Setup] USPC system bootstrap and setup finished successfully.")
    else:
        logger.error(f"[Setup] USPC installation returned error code {rc}.")

    return rc
