"""Storage directory management, disk verification, and migration."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import ensure_directory, get_free_disk_space_gb

logger = get_logger("storage")


@dataclass
class StoragePaths:
    """Standardized directory layout for USPC data."""

    base_data: Path
    nextcloud_data: Path
    postgres_data: Path
    redis_data: Path
    media_cache: Path
    headscale_data: Path
    base_config: Path
    nextcloud_config: Path
    headscale_config: Path
    logs_dir: Path


class StorageManager:
    """Manages persistent volumes, storage layout, validation, and migration."""

    def __init__(
        self, data_path: str | Path, config_path: str | Path, min_free_space_gb: float = 20.0
    ):
        self.data_path = Path(data_path).expanduser().resolve()
        self.config_path = Path(config_path).expanduser().resolve()
        self.min_free_space_gb = min_free_space_gb

    def get_paths(self) -> StoragePaths:
        """Resolve all persistent storage directory paths."""
        return StoragePaths(
            base_data=self.data_path,
            nextcloud_data=self.data_path / "nextcloud",
            postgres_data=self.data_path / "postgres",
            redis_data=self.data_path / "redis",
            media_cache=self.data_path / "media_cache",
            headscale_data=self.data_path / "headscale",
            base_config=self.config_path,
            nextcloud_config=self.config_path / "nextcloud",
            headscale_config=self.config_path / "headscale",
            logs_dir=self.config_path / "logs",
        )

    def initialize_storage(self) -> StoragePaths:
        """Create all required persistent data directories with safe permissions."""
        paths = self.get_paths()
        # Enforce free space validation
        self.validate_space()

        # Create all subdirectories
        for p in (
            paths.base_data,
            paths.nextcloud_data,
            paths.postgres_data,
            paths.redis_data,
            paths.media_cache,
            paths.headscale_data,
            paths.base_config,
            paths.nextcloud_config,
            paths.headscale_config,
            paths.logs_dir,
        ):
            ensure_directory(p, mode=0o750)

        # Verify read/write
        self.verify_read_write(paths.base_data)
        self.verify_read_write(paths.base_config)
        logger.info("All persistent storage directories initialized and verified.")
        return paths

    def validate_space(self) -> None:
        """Validate that host disk has sufficient free capacity."""
        free_gb = get_free_disk_space_gb(self.data_path)
        if free_gb < self.min_free_space_gb:
            raise ValueError(
                f"Insufficient disk space at '{self.data_path}'. "
                f"Available: {free_gb:.1f} GB, Required: {self.min_free_space_gb:.1f} GB"
            )
        logger.debug(f"Storage capacity check passed: {free_gb:.1f} GB free at {self.data_path}")

    def verify_read_write(self, target_dir: Path) -> bool:
        """Perform a test write/read/delete cycle to verify storage integrity."""
        ensure_directory(target_dir)
        test_file = target_dir / ".uspc_rw_check.tmp"
        test_content = "uspc_storage_verification_payload"
        try:
            test_file.write_text(test_content, encoding="utf-8")
            read_back = test_file.read_text(encoding="utf-8")
            if read_back != test_content:
                raise OSError("Data read back does not match written content")
            test_file.unlink()
            return True
        except Exception as e:
            raise OSError(f"Storage read/write verification failed at '{target_dir}': {e}") from e

    def migrate_data(self, new_data_path: str | Path) -> bool:
        """Migrate all persistent data to a new target directory safely."""
        target = Path(new_data_path).expanduser().resolve()
        if target == self.data_path:
            logger.info("Source and destination storage paths are identical. Skipping migration.")
            return True

        free_gb = get_free_disk_space_gb(target)
        if free_gb < self.min_free_space_gb:
            raise ValueError(
                f"Target location '{target}' does not have enough free space ({free_gb:.1f} GB)"
            )

        ensure_directory(target, mode=0o750)
        logger.info(f"Copying data from '{self.data_path}' to '{target}'...")

        # Copy data recursively
        for item in self.data_path.iterdir():
            dest_item = target / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)

        self.verify_read_write(target)
        self.data_path = target
        logger.info(f"Data successfully migrated to '{target}'")
        return True

    def get_usage_stats(self) -> dict[str, float]:
        """Calculate disk usage across subdirectories in MB."""
        paths = self.get_paths()
        stats: dict[str, float] = {}
        for name, p in [
            ("nextcloud", paths.nextcloud_data),
            ("postgres", paths.postgres_data),
            ("redis", paths.redis_data),
            ("media_cache", paths.media_cache),
            ("headscale", paths.headscale_data),
        ]:
            total_bytes = 0
            if p.exists():
                for root, _, files in os.walk(p):
                    for f in files:
                        try:
                            total_bytes += (Path(root) / f).stat().st_size
                        except OSError:
                            pass
            stats[name] = round(total_bytes / (1024 * 1024), 2)
        return stats
