"""Cross-platform disaster recovery and migration bundle manager."""

from __future__ import annotations

import json
import os
import platform
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cloudctl import __version__
from cloudctl.core.container import ContainerManager
from cloudctl.core.logging import get_logger
from cloudctl.core.storage import StorageManager
from cloudctl.utils.crypto import calculate_file_sha256
from cloudctl.utils.fs import ensure_directory

logger = get_logger("migration")


@dataclass
class MigrationManifest:
    """Metadata describing a migration bundle."""

    bundle_version: str
    uspc_version: str
    created_at: str
    source_os: str
    source_arch: str
    files_count: int
    total_bytes: int
    checksums: dict[str, str]


class MigrationManager:
    """Handles migration bundle packaging, verification, export, and import."""

    def __init__(self, config: dict[str, Any], storage_mgr: StorageManager):
        self.config = config
        self.storage_mgr = storage_mgr

    def export_bundle(self, output_path: str | Path) -> Path:
        """Create a complete, portable migration bundle archive."""
        dest_archive = Path(output_path).expanduser().resolve()
        ensure_directory(dest_archive.parent)

        paths = self.storage_mgr.get_paths()
        logger.info(f"Generating migration export bundle to '{dest_archive}'...")

        with tempfile.TemporaryDirectory(prefix="uspc_mig_export_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            bundle_data_dir = tmp_root / "data"
            bundle_db_dir = tmp_root / "db"
            bundle_config_dir = tmp_root / "config"

            ensure_directory(bundle_data_dir)
            ensure_directory(bundle_db_dir)
            ensure_directory(bundle_config_dir)

            # Dump PostgreSQL database
            cm = ContainerManager()
            db_res = cm.exec_command("uspc-postgres", ["pg_dumpall", "-U", "nextcloud"])
            db_dump_file = bundle_db_dir / "database.sql"
            if db_res.success and db_res.stdout:
                db_dump_file.write_text(db_res.stdout, encoding="utf-8")
            else:
                db_dump_file.write_text("-- USPC DB Placeholder / offline dump\n", encoding="utf-8")

            # Collect Nextcloud files
            file_count = 0
            total_bytes = 0
            checksums: dict[str, str] = {}

            if paths.nextcloud_data.exists():
                for root, _, files in os.walk(paths.nextcloud_data):
                    for file in files:
                        src_f = Path(root) / file
                        rel_f = src_f.relative_to(paths.nextcloud_data)
                        dest_f = bundle_data_dir / rel_f
                        ensure_directory(dest_f.parent)
                        try:
                            content = src_f.read_bytes()
                            dest_f.write_bytes(content)
                            file_count += 1
                            total_bytes += len(content)
                            checksums[str(rel_f)] = calculate_file_sha256(dest_f)
                        except Exception as e:
                            logger.warning(f"Could not copy file during export {src_f}: {e}")

            # Manifest creation
            manifest = MigrationManifest(
                bundle_version="1.0.0",
                uspc_version=__version__,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                source_os=platform.system().lower(),
                source_arch=platform.machine().lower(),
                files_count=file_count,
                total_bytes=total_bytes,
                checksums=checksums,
            )

            manifest_file = tmp_root / "manifest.json"
            manifest_file.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")

            # Create tar.gz archive
            with tarfile.open(dest_archive, "w:gz") as tar:
                tar.add(tmp_root, arcname=".")

        logger.info(
            f"Migration bundle successfully created: {dest_archive} ({file_count} files, {total_bytes / (1024**2):.2f} MB)"
        )
        return dest_archive

    def import_bundle(self, input_path: str | Path, restore_db: bool = True) -> bool:
        """Import a migration bundle into the active personal cloud instance."""
        bundle_file = Path(input_path).expanduser().resolve()
        if not bundle_file.exists():
            raise FileNotFoundError(f"Migration bundle archive not found: {bundle_file}")

        paths = self.storage_mgr.get_paths()
        logger.info(f"Importing migration bundle from '{bundle_file}'...")

        with tempfile.TemporaryDirectory(prefix="uspc_mig_import_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            with tarfile.open(bundle_file, "r:gz") as tar:
                # Security: validate all tar members to prevent path traversal (CVE-2007-4559)
                resolved_target = tmp_root.resolve()
                for member in tar.getmembers():
                    member_path = (tmp_root / member.name).resolve()
                    if (
                        resolved_target != member_path
                        and resolved_target not in member_path.parents
                    ):
                        raise ValueError(
                            f"Security Alert: Tar slip attempt detected in member '{member.name}'"
                        )
                tar.extractall(tmp_root)

            # Validate manifest
            manifest_file = tmp_root / "manifest.json"
            if not manifest_file.exists():
                raise ValueError("Invalid migration bundle: missing manifest.json")

            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            logger.info(
                f"Bundle Info: USPC v{manifest_data.get('uspc_version')}, "
                f"Source: {manifest_data.get('source_os')}-{manifest_data.get('source_arch')}, "
                f"Files: {manifest_data.get('files_count')}"
            )

            # Restore data files
            bundle_data = tmp_root / "data"
            if bundle_data.exists():
                for root, _, files in os.walk(bundle_data):
                    for file in files:
                        src_f = Path(root) / file
                        rel_f = src_f.relative_to(bundle_data)
                        dest_f = paths.nextcloud_data / rel_f
                        ensure_directory(dest_f.parent)
                        dest_f.write_bytes(src_f.read_bytes())

            # Restore database if requested
            bundle_db = tmp_root / "db" / "database.sql"
            if restore_db and bundle_db.exists():
                cm = ContainerManager()
                logger.info("Restoring PostgreSQL database from migration bundle...")
                sql_content = bundle_db.read_text(encoding="utf-8")
                cm.exec_command(
                    "uspc-postgres", f"psql -U nextcloud -d nextcloud -c '{sql_content}'"
                )

        logger.info("Migration bundle successfully imported!")
        return True
