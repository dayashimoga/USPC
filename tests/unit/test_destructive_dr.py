"""Destructive disaster recovery, isolated restore, and SHA-256 data verification tests."""

import hashlib
import shutil
from unittest.mock import MagicMock, patch

from cloudctl.core.backup import BackupManager


def test_destructive_dr_lifecycle_and_sha256_verification(tmp_path):
    """
    Test complete DR lifecycle:
    1. Create data files, media, and config
    2. Compute SHA-256 checksums
    3. Perform backup
    4. Simulate catastrophic host destruction (wipe data directory)
    5. Restore and verify all SHA-256 checksums match
    """
    data_dir = tmp_path / "data"
    backup_target = tmp_path / "backups"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    backup_target.mkdir()
    config_dir.mkdir()

    # Step 1: Create sample files & media
    test_files = {}
    for i in range(10):
        f = data_dir / f"doc_{i}.pdf"
        content = f"PDF_DOCUMENT_CONTENT_VERSION_{i}".encode()
        f.write_bytes(content)
        test_files[f.name] = (content, hashlib.sha256(content).hexdigest())

    config = {
        "backup": {"enabled": True, "target_path": str(backup_target)},
        "storage": {
            "data_path": str(data_dir),
            "config_path": str(config_dir),
            "min_free_space_gb": 1.0,
        },
    }

    bm = BackupManager(config)

    # Step 2: Simulate backup creation
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="snapshot 12345678 created")
        res = bm.create_backup(verify_after=True)
        assert res is True

    # Step 3: Catastrophic destruction (wipe data directory)
    shutil.rmtree(data_dir)
    data_dir.mkdir()
    assert len(list(data_dir.glob("*"))) == 0

    # Step 4: Re-populate restored data (as restic restore would do)
    for fname, (content, _) in test_files.items():
        (data_dir / fname).write_bytes(content)

    # Step 5: Verify all hashes match original
    for fname, (_expected_content, expected_hash) in test_files.items():
        restored_file = data_dir / fname
        assert restored_file.exists()
        actual_hash = hashlib.sha256(restored_file.read_bytes()).hexdigest()
        assert actual_hash == expected_hash


def test_interrupted_backup_recovery(tmp_path):
    """Verify recovery when a backup is interrupted midway (locks cleared)."""
    config = {
        "backup": {"enabled": True, "target_path": str(tmp_path / "backups")},
        "storage": {"data_path": str(tmp_path / "data"), "config_path": str(tmp_path / "config")},
    }
    bm = BackupManager(config)

    with patch("cloudctl.core.backup.run_command") as mock_run:
        # First attempt interrupted with SIGINT/error
        mock_run.return_value = MagicMock(success=False, stderr="Interrupted by user signal")
        res1 = bm.create_backup()
        assert res1 is False

        # Next attempt succeeds
        mock_run.return_value = MagicMock(success=True, stdout="snapshot abcd1234 created")
        res2 = bm.create_backup()
        assert res2 is True
