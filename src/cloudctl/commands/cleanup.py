"""Clean cache, temporary files, and stale transcode/thumbnail assets."""

from __future__ import annotations

import argparse
from pathlib import Path

from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger
from cloudctl.core.storage import StorageManager
from cloudctl.utils.fs import remove_path_safely

logger = get_logger("cmd.cleanup")


def execute_cleanup(args: argparse.Namespace) -> int:
    """Execute safe disk space cleanup for cache and temporary files."""
    cfg_mgr = ConfigManager(config_path=getattr(args, "config", None))
    config = cfg_mgr.load_config()

    storage_mgr = StorageManager(
        data_path=config["storage"]["data_path"],
        config_path=config["storage"]["config_path"],
    )
    paths = storage_mgr.get_paths()

    dry_run = getattr(args, "dry_run", False)
    purge_thumbnails = getattr(args, "purge_thumbnails", False)
    purge_transcodes = getattr(args, "purge_transcodes", False)

    logger.info(
        f"Scanning for cleanable cache and temporary data{' [DRY-RUN]' if dry_run else ''}..."
    )

    targets: list[tuple[str, Path]] = []
    if paths.media_cache.exists():
        if purge_thumbnails:
            targets.append(("Thumbnail cache", paths.media_cache / "thumbnails"))
        if purge_transcodes:
            targets.append(("Transcode cache", paths.media_cache / "transcoded"))

    # Also clean temporary test / dump files
    tmp_dump = paths.base_config / "postgres_backup.sql"
    if tmp_dump.exists():
        targets.append(("Stale SQL dump", tmp_dump))

    total_bytes = 0
    found_items = []

    for label, target in targets:
        if target.exists():
            if target.is_dir():
                size = sum(f.stat().st_size for f in target.glob("**/*") if f.is_file())
            else:
                size = target.stat().st_size
            total_bytes += size
            found_items.append((label, target, size))

    print("\n" + "=" * 65)
    print(" USPC Storage & Cache Cleanup")
    print("=" * 65)
    if not found_items:
        print(" No cleanable cache files or stale temporary assets found.")
    else:
        for label, target, size in found_items:
            print(f" * {label:<22} : {target} ({size / (1024 * 1024):.2f} MB)")
        print(f"\n Total Reclaimable Space: {total_bytes / (1024 * 1024):.2f} MB")

    if not dry_run and found_items:
        print("\n Executing cleanup...")
        for label, target, _ in found_items:
            remove_path_safely(target)
            logger.info(f"Cleaned {label} at {target}")
        print(" Cleanup completed successfully!")
    elif dry_run and found_items:
        print("\n [DRY-RUN] No files were removed. Re-run without --dry-run to apply.")
    print("=" * 65 + "\n")
    return 0
