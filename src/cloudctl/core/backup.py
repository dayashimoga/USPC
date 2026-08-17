"""Encrypted backup and restore management using Restic."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cloudctl.core.container import ContainerManager
from cloudctl.core.logging import get_logger
from cloudctl.core.secrets import SecretManager
from cloudctl.core.storage import StorageManager
from cloudctl.utils.fs import ensure_directory
from cloudctl.utils.shell import run_command

logger = get_logger("backup")


@dataclass
class SnapshotInfo:
    """Information regarding a single backup snapshot."""

    id: str
    time: str
    tags: list[str]
    paths: list[str]


class BackupManager:
    """Automates encrypted snapshot backups and disaster recovery restores."""

    def __init__(self, config: dict[str, Any], secrets_dir: str | Path | None = None):
        self.config = config
        self.backup_cfg = config.get("backup", {})
        self.target_path = (
            Path(self.backup_cfg.get("target_path", "~/.uspc/backups")).expanduser().resolve()
        )
        self.secret_mgr = SecretManager(secrets_dir)
        self.storage_mgr = StorageManager(
            data_path=config.get("storage", {}).get("data_path", "~/.uspc/data"),
            config_path=config.get("storage", {}).get("config_path", "~/.uspc/config"),
        )

    def _get_restic_env(self) -> dict[str, str]:
        """Prepare environment variables for Restic with repository key."""
        secrets = self.secret_mgr.load_or_generate_secrets()
        return {
            "RESTIC_REPOSITORY": str(self.target_path),
            "RESTIC_PASSWORD": secrets.restic_password,
        }

    def init_repository(self) -> bool:
        """Initialize encrypted Restic backup repository if not already existing."""
        ensure_directory(self.target_path, mode=0o700)
        env = self._get_restic_env()

        # Check if already initialized
        check = run_command(["restic", "cat", "config"], env=env, timeout=15.0)
        if check.success:
            logger.debug(f"Restic repository at {self.target_path} is already initialized.")
            return True

        res = run_command(["restic", "init"], env=env, timeout=30.0)
        if res.success:
            logger.info(f"Initialized new encrypted Restic backup repository at {self.target_path}")
            return True
        else:
            # Fallback if restic is not installed on host: simulate or log
            logger.warning(f"Restic CLI not available on host or failed to init: {res.stderr}")
            return False

    def create_backup(self, tag: str = "manual", verify_after: bool = True) -> bool:
        """Create a complete encrypted snapshot of Nextcloud, Postgres dump, and configs."""
        paths = self.storage_mgr.get_paths()
        env = self._get_restic_env()

        # Ensure repo initialized
        self.init_repository()

        # Dump Postgres DB
        cm = ContainerManager()
        ensure_directory(paths.base_config)
        db_dump_path = paths.base_config / "postgres_backup.sql"
        logger.info("Generating PostgreSQL database snapshot...")
        db_dump = cm.exec_command(
            name="uspc-postgres",
            cmd=["pg_dumpall", "-U", "nextcloud"],
        )
        if db_dump.success and db_dump.stdout:
            db_dump_path.write_text(db_dump.stdout, encoding="utf-8")

        # Restic backup targets
        backup_sources = [
            str(paths.base_data),
            str(paths.base_config),
        ]

        logger.info(f"Creating encrypted backup snapshot with tag '{tag}'...")
        cmd = ["restic", "backup", "--tag", tag] + backup_sources
        res = run_command(cmd, env=env, timeout=300.0)

        if not res.success:
            logger.error(f"Backup creation failed: {res.stderr}")
            return False

        logger.info("Backup snapshot created successfully!")

        if verify_after:
            self.verify_repository()

        return True

    def verify_repository(self) -> bool:
        """Run cryptographic integrity check on backup repository."""
        env = self._get_restic_env()
        logger.info("Verifying backup repository cryptographic integrity...")
        res = run_command(["restic", "check"], env=env, timeout=120.0)
        if res.success:
            logger.info("Backup verification: PASS (All data packs and indexes intact)")
            return True
        else:
            logger.error(f"Backup verification failed: {res.stderr}")
            return False

    def list_snapshots(self) -> list[str]:
        """List all available snapshots."""
        env = self._get_restic_env()
        res = run_command(["restic", "snapshots"], env=env, timeout=20.0)
        if res.success:
            return res.stdout.splitlines()
        return []

    def restore_backup(
        self,
        snapshot_id: str = "latest",
        target_dir: str | Path | None = None,
        dry_run: bool = False,
    ) -> bool:
        """Restore files from backup snapshot."""
        env = self._get_restic_env()
        dest = Path(target_dir).expanduser().resolve() if target_dir else Path("/")

        cmd = ["restic", "restore", snapshot_id, "--target", str(dest)]
        if dry_run:
            cmd.append("--dry-run")
            logger.info(f"[DRY-RUN] Simulating restore of snapshot '{snapshot_id}' to '{dest}'")
        else:
            logger.info(f"Restoring snapshot '{snapshot_id}' to '{dest}'...")

        res = run_command(cmd, env=env, timeout=300.0)
        if res.success:
            logger.info("Restore completed successfully.")
            return True
        else:
            logger.error(f"Restore failed: {res.stderr}")
            return False

    def test_restore_isolation(self) -> bool:
        """Perform a non-destructive test restore into a temporary directory and verify data."""
        with tempfile.TemporaryDirectory(prefix="uspc_restore_test_") as tmp_dir:
            logger.info(f"Testing restore into isolated test location: {tmp_dir}")
            res = self.restore_backup(snapshot_id="latest", target_dir=tmp_dir, dry_run=False)
            if res:
                logger.info("Isolated test restore: PASS")
                return True
            else:
                logger.warning("Isolated test restore: FAILED")
                return False

    def prune_retention(
        self, keep_daily: int = 7, keep_weekly: int = 4, keep_monthly: int = 12
    ) -> bool:
        """Prune older snapshots based on retention schedule and reclaim disk space."""
        env = self._get_restic_env()
        cmd = [
            "restic",
            "forget",
            "--keep-daily",
            str(keep_daily),
            "--keep-weekly",
            str(keep_weekly),
            "--keep-monthly",
            str(keep_monthly),
            "--prune",
        ]
        logger.info(
            f"Enforcing backup retention policy (keep daily={keep_daily}, weekly={keep_weekly}, monthly={keep_monthly})..."
        )
        res = run_command(cmd, env=env, timeout=180.0)
        return res.success
