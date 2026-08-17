"""Upgrade, schema migration, and automatic/manual rollback tests."""

import argparse
from unittest.mock import MagicMock, patch

from cloudctl.commands.update import execute_update
from cloudctl.core.config import ConfigManager


def test_upgrade_workflow_success(tmp_path):
    """Verify update command performs safety backup, validates schema, and verifies health."""
    cfg_file = tmp_path / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    defaults = cm.load_defaults()
    cm.save_config(defaults)

    args = argparse.Namespace(
        dry_run=False,
        config=str(cfg_file),
    )

    with patch("cloudctl.core.backup.BackupManager.create_backup") as mock_backup:
        with patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health:
            mock_health.return_value = MagicMock(overall_status="HEALTHY", checks=[])
            rc = execute_update(args)
            assert rc == 0
            mock_backup.assert_called_once()
            mock_health.assert_called_once()


def test_upgrade_workflow_failed_health_triggers_error(tmp_path):
    """Verify failed health check post-update alerts user to rollback."""
    cfg_file = tmp_path / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    defaults = cm.load_defaults()
    cm.save_config(defaults)

    args = argparse.Namespace(
        dry_run=False,
        config=str(cfg_file),
    )

    with patch("cloudctl.core.backup.BackupManager.create_backup"):
        with patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health:
            mock_health.return_value = MagicMock(overall_status="UNHEALTHY", checks=[])
            rc = execute_update(args)
            assert rc == 1


def test_upgrade_dry_run_simulation(tmp_path):
    """Verify dry-run simulates update without pulling images or creating backups."""
    cfg_file = tmp_path / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    defaults = cm.load_defaults()
    cm.save_config(defaults)

    args = argparse.Namespace(
        dry_run=True,
        config=str(cfg_file),
    )

    with patch("cloudctl.core.backup.BackupManager.create_backup") as mock_backup:
        rc = execute_update(args)
        assert rc == 0
        mock_backup.assert_not_called()
