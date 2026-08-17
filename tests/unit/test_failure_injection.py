"""Failure injection and edge-case testing for USPC core subsystems."""

import os
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudctl.commands.cleanup import execute_cleanup
from cloudctl.core.backup import BackupManager
from cloudctl.core.migration import MigrationManager
from cloudctl.core.storage import StorageManager
from src.media.config import MediaConfig
from src.media.indexer import MediaIndexer
from src.media.models import MediaDatabase


def test_tar_slip_prevention(temp_dir: Path):
    import io

    storage_mgr = StorageManager(temp_dir / "data", temp_dir / "config", min_free_space_gb=0.01)
    storage_mgr.initialize_storage()

    mig_mgr = MigrationManager({}, storage_mgr)

    # Construct a malicious tar containing path traversal filename
    evil_tar = temp_dir / "evil_bundle.tar.gz"
    with tarfile.open(evil_tar, "w:gz") as tar:
        tarinfo = tarfile.TarInfo(name="../../evil_script.sh")
        payload = b"echo evil"
        tarinfo.size = len(payload)
        tar.addfile(tarinfo, io.BytesIO(payload))

    with pytest.raises(ValueError) as exc:
        mig_mgr.import_bundle(evil_tar)
    assert "Tar slip attempt detected" in str(exc.value)


def test_corrupted_media_file_handling(temp_dir: Path):
    data_dir = temp_dir / "corrupted_media"
    data_dir.mkdir()
    cache_dir = temp_dir / "cache"

    # Create 0-byte file and random binary garbage file
    empty_file = data_dir / "zero_byte.mp4"
    empty_file.write_bytes(b"")

    garbage_file = data_dir / "corrupt.jpg"
    garbage_file.write_bytes(os.urandom(1024))

    cfg = MediaConfig(data_path=data_dir, cache_path=cache_dir)
    db = MediaDatabase(cfg.db_path)
    indexer = MediaIndexer(cfg, db)

    # Sync should succeed without unhandled exceptions
    stats = indexer.sync_all()
    assert stats["total"] == 2

    # Both items should be saved in DB
    items, total = db.list_items()
    assert total == 2


def test_backup_pruning_and_retention(mock_config_dict: dict, temp_dir: Path):
    bm = BackupManager(mock_config_dict, secrets_dir=temp_dir / "secrets")
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.return_value = MagicMock(
            success=True, stdout="Snapshots forgotten", stderr="", returncode=0
        )
        assert bm.prune_retention(keep_daily=7, keep_weekly=4, keep_monthly=12) is True


def test_storage_usage_stats_and_migration(temp_dir: Path):
    sm = StorageManager(temp_dir / "src_data", temp_dir / "src_config", min_free_space_gb=0.01)
    paths = sm.initialize_storage()

    # Write files
    (paths.nextcloud_data / "sample.dat").write_bytes(b"A" * 1024 * 100)  # 100 KB
    (paths.postgres_data / "pg.dat").write_bytes(b"B" * 1024 * 50)

    stats = sm.get_usage_stats()
    assert "nextcloud" in stats
    assert "postgres" in stats
    assert stats["nextcloud"] >= 0.09

    # Migration to new directory
    new_data = temp_dir / "new_data_dir"
    assert sm.migrate_data(new_data) is True
    assert (new_data / "nextcloud" / "sample.dat").exists()


def test_cleanup_command_execution(temp_dir: Path):
    data_dir = temp_dir / "clean_data"
    config_dir = temp_dir / "clean_config"
    sm = StorageManager(data_dir, config_dir, min_free_space_gb=0.01)
    paths = sm.initialize_storage()

    # Create dummy thumbnails and transcodes
    thumb_dir = paths.media_cache / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "t1.webp").write_bytes(b"X" * 1024)

    trans_dir = paths.media_cache / "transcoded"
    trans_dir.mkdir(parents=True, exist_ok=True)
    (trans_dir / "v1.mp4").write_bytes(b"Y" * 1024)

    # Dry-run execution
    args_dry = MagicMock(
        config=None,
        dry_run=True,
        purge_thumbnails=True,
        purge_transcodes=True,
    )
    with patch("cloudctl.core.config.ConfigManager.load_config") as mock_load:
        mock_load.return_value = {
            "storage": {
                "data_path": str(data_dir),
                "config_path": str(config_dir),
            }
        }
        res_dry = execute_cleanup(args_dry)
        assert res_dry == 0
        assert (thumb_dir / "t1.webp").exists()

        # Real execution
        args_real = MagicMock(
            config=None,
            dry_run=False,
            purge_thumbnails=True,
            purge_transcodes=True,
        )
        res_real = execute_cleanup(args_real)
        assert res_real == 0
        assert not (thumb_dir / "t1.webp").exists()
