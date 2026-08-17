"""Unit tests for backup and migration bundle operations."""

from pathlib import Path

from cloudctl.core.backup import BackupManager
from cloudctl.core.migration import MigrationManager
from cloudctl.core.storage import StorageManager


def test_backup_manager(mock_config_dict: dict, temp_dir: Path):
    sec_dir = temp_dir / "secrets"
    bm = BackupManager(mock_config_dict, secrets_dir=sec_dir)
    env = bm._get_restic_env()
    assert "RESTIC_REPOSITORY" in env
    assert "RESTIC_PASSWORD" in env


def test_migration_manager(mock_config_dict: dict, temp_dir: Path):
    data_p = temp_dir / "data"
    cfg_p = temp_dir / "config"
    sm = StorageManager(data_p, cfg_p, min_free_space_gb=0.1)
    paths = sm.initialize_storage()

    # Create dummy user file in nextcloud storage
    test_user_file = paths.nextcloud_data / "documents" / "note.txt"
    test_user_file.parent.mkdir(parents=True, exist_ok=True)
    test_user_file.write_text("Hello Migration!", encoding="utf-8")

    mig = MigrationManager(mock_config_dict, sm)
    bundle_dest = temp_dir / "export_bundle.tar.gz"

    # Export
    out = mig.export_bundle(bundle_dest)
    assert out.exists()
    assert bundle_dest.stat().st_size > 0

    # Clean target directory and import
    target_data_p = temp_dir / "restored_data"
    target_cfg_p = temp_dir / "restored_config"
    target_sm = StorageManager(target_data_p, target_cfg_p, min_free_space_gb=0.1)
    target_sm.initialize_storage()

    target_mig = MigrationManager(mock_config_dict, target_sm)
    success = target_mig.import_bundle(bundle_dest, restore_db=False)
    assert success is True

    restored_file = target_sm.get_paths().nextcloud_data / "documents" / "note.txt"
    assert restored_file.exists()
    assert restored_file.read_text(encoding="utf-8") == "Hello Migration!"
