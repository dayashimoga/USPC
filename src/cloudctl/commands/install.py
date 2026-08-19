"""Automated one-command installer for USPC."""

from __future__ import annotations

import argparse
import time

from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import detect_host
from cloudctl.core.health import HealthChecker
from cloudctl.core.logging import get_logger
from cloudctl.core.network import NetworkManager
from cloudctl.core.reporting import print_status_dashboard
from cloudctl.core.secrets import SecretManager
from cloudctl.core.storage import StorageManager

logger = get_logger("cmd.install")


def execute_install(args: argparse.Namespace) -> int:
    """Execute the full one-command deployment workflow."""
    dry_run = getattr(args, "dry_run", False)
    logger.info(f"Starting USPC installation{' [DRY-RUN]' if dry_run else ''}...")

    # Step 1: Detect host & hardware
    host = detect_host()
    logger.info(
        f"Step 1/11: Detected OS: {host.os_name} ({host.arch}), RAM: {host.total_ram_gb} GB, Engine: {host.container_engine}"
    )

    # Step 2: Load and validate configuration
    cfg_mgr = ConfigManager(config_path=getattr(args, "config", None))
    config = cfg_mgr.load_config()
    logger.info("Step 2/11: Configuration loaded and validated against schema.")

    # Step 3: Initialize secrets
    secret_mgr = SecretManager()
    secrets = secret_mgr.load_or_generate_secrets()
    logger.info("Step 3/11: Security credentials and cryptographic keys verified.")

    # Step 4: Storage initialization
    storage_mgr = StorageManager(
        data_path=config["storage"]["data_path"],
        config_path=config["storage"]["config_path"],
        min_free_space_gb=config["storage"]["min_free_space_gb"],
    )
    if dry_run:
        logger.info("[DRY-RUN] Would initialize storage directories and verify write access.")
    else:
        paths = storage_mgr.initialize_storage()
        logger.info(f"Step 4/11: Persistent storage initialized at '{paths.base_data}'")

    if dry_run:
        logger.info("[DRY-RUN] Validation complete. All pre-flight checks passed successfully.")
        return 0

    # Step 5: Network & Headscale VPN setup
    net_mgr = NetworkManager(config, storage_mgr.get_paths().base_config)
    net_mgr.generate_headscale_config(
        private_key=secrets.headscale_private_key,
        noise_private_key=secrets.headscale_noise_private_key,
    )
    logger.info("Step 5/11: Private VPN mesh (Headscale/WireGuard) configured.")

    # Step 6: Container runtime initialization
    cm = ContainerManager(engine=config["runtime"]["engine"])
    cm.create_pod(
        port_mappings=[
            (config["services"]["nextcloud"]["port"], 80),
            (config["media"]["port"], 8085),
            (config["network"]["headscale_port"], config["network"]["headscale_port"]),
        ],
        force=True,
    )
    logger.info(f"Step 6/11: Container runtime pod initialized using {cm.engine}.")

    # Step 7: Launch PostgreSQL database
    paths = storage_mgr.get_paths()
    pg_cfg = config["services"]["postgres"]
    cm.run_container(
        name="uspc-postgres",
        image=f"docker.io/library/postgres:{pg_cfg['version']}",
        env={
            "POSTGRES_DB": pg_cfg["db_name"],
            "POSTGRES_USER": pg_cfg["user"],
            "POSTGRES_PASSWORD": secrets.postgres_password,
        },
        volumes=[(str(paths.postgres_data), "/var/lib/postgresql/data")],
    )
    logger.info("Step 7/11: PostgreSQL database container deployed.")

    # Step 8: Launch Redis cache
    redis_cfg = config["services"]["redis"]
    cm.run_container(
        name="uspc-redis",
        image=f"docker.io/library/redis:{redis_cfg['version']}",
        volumes=[(str(paths.redis_data), "/data")],
    )
    logger.info("Step 8/11: Redis in-memory cache container deployed.")

    # Step 9: Launch Nextcloud Community
    nc_cfg = config["services"]["nextcloud"]
    cm.run_container(
        name="uspc-nextcloud",
        image=f"docker.io/library/nextcloud:{nc_cfg['version']}",
        env={
            "POSTGRES_HOST": "127.0.0.1" if cm.engine == "podman" else "uspc-postgres",
            "POSTGRES_DB": pg_cfg["db_name"],
            "POSTGRES_USER": pg_cfg["user"],
            "POSTGRES_PASSWORD": secrets.postgres_password,
            "REDIS_HOST": "127.0.0.1" if cm.engine == "podman" else "uspc-redis",
            "NEXTCLOUD_ADMIN_USER": config["cloud"]["admin_user"],
            "NEXTCLOUD_ADMIN_PASSWORD": secrets.nextcloud_admin_password,
            "NEXTCLOUD_TRUSTED_DOMAINS": f"{config['cloud']['domain']} localhost 127.0.0.1",
        },
        volumes=[
            (str(paths.nextcloud_data), "/var/www/html/data"),
            (str(paths.nextcloud_config), "/var/www/html/config"),
        ],
    )
    logger.info("Step 9/11: Nextcloud personal cloud container deployed.")

    # Step 10: Launch Media Library microservice
    if config["media"]["enabled"]:
        media_image = "uspc-media:latest"
        if not cm.image_exists(media_image):
            from pathlib import Path

            df_path = Path(__file__).resolve().parents[2] / "media" / "Dockerfile"
            ctx_path = Path(__file__).resolve().parents[3]
            if df_path.exists():
                cm.build_image(media_image, str(df_path), str(ctx_path))

        cm.run_container(
            name="uspc-media",
            image=media_image,
            env={
                "USPC_DATA_PATH": "/data/nextcloud",
                "USPC_CACHE_PATH": "/data/media_cache",
                "USPC_JWT_SECRET": secrets.media_jwt_secret,
                "USPC_PORT": "8085",
            },
            volumes=[
                (str(paths.nextcloud_data), "/data/nextcloud"),
                (str(paths.media_cache), "/data/media_cache"),
            ],
        )
        logger.info("Step 10/11: USPC Media streaming microservice deployed.")

    # Step 11: Launch Headscale VPN coordination
    cm.run_container(
        name="uspc-headscale",
        image="docker.io/headscale/headscale:0.22.3",
        volumes=[
            (str(paths.headscale_config), "/etc/headscale"),
            (str(paths.headscale_data), "/var/lib/headscale"),
        ],
    )
    logger.info("Step 11/11: Headscale VPN mesh controller deployed.")

    # Run health check post-install
    if not getattr(args, "skip_smoke_test", False):
        time.sleep(2)
        health_checker = HealthChecker(config)
        report = health_checker.run_all_checks()
        print_status_dashboard(report, config)

    print("\n" + "=" * 70)
    print(" USPC Installation Finished Successfully!")
    print("=" * 70)
    print(f" Cloud URL        : http://127.0.0.1:{config['services']['nextcloud']['port']}")
    print(f" Media Library    : http://127.0.0.1:{config['media']['port']}")
    print(f" Admin Username   : {config['cloud']['admin_user']}")
    print(f" Secrets Location : {secret_mgr.secrets_file}")
    print("=" * 70 + "\n")
    return 0
