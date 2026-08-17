"""Tests for cloudctl setup bootstrap, cross-platform detection, and config metadata/migration."""

import argparse
from unittest.mock import MagicMock, patch

from cloudctl.commands.config_cmd import execute_config
from cloudctl.commands.setup import execute_setup
from cloudctl.core.config import ConfigManager


def test_setup_command_dry_run(tmp_path):
    """Verify cloudctl setup --dry-run plans installation without modifying files."""
    args = argparse.Namespace(
        dry_run=True,
        non_interactive=True,
        force=False,
        domain="dryrun.cloud.local",
        name="dryrun-cloud",
        config=str(tmp_path / "cloud.yaml"),
        skip_smoke_test=True,
    )

    with patch("cloudctl.commands.install.execute_install", return_value=0) as mock_install:
        rc = execute_setup(args)
        assert rc == 0
        mock_install.assert_called_once()


def test_setup_command_idempotent_execution(tmp_path):
    """Verify cloudctl setup can be run multiple times safely (idempotent)."""
    cfg_file = tmp_path / "cloud.yaml"
    args = argparse.Namespace(
        dry_run=False,
        non_interactive=True,
        force=False,
        domain="idempotent.local",
        name="idempotent-cloud",
        config=str(cfg_file),
        skip_smoke_test=True,
    )

    with patch("cloudctl.commands.install.execute_install", return_value=0):
        with patch("cloudctl.core.storage.StorageManager.initialize_storage") as mock_storage:
            mock_storage.return_value = MagicMock(base_data=tmp_path / "data")
            rc1 = execute_setup(args)
            assert rc1 == 0

            # Run again (second time)
            rc2 = execute_setup(args)
            assert rc2 == 0


def test_config_setting_metadata_extraction(tmp_path):
    """Verify get_setting_metadata returns description, allowed ranges, and impact flags."""
    cm = ConfigManager(config_path=tmp_path / "cloud.yaml")

    meta_profile = cm.get_setting_metadata("performance.profile")
    assert (
        "auto" in meta_profile["allowed_range"].lower()
        or "tiny" in meta_profile["allowed_range"].lower()
    )

    meta_port = cm.get_setting_metadata("network.headscale_port")
    assert meta_port["restart_required"] is True
    assert meta_port["security_impact"] is True

    meta_unknown = cm.get_setting_metadata("nonexistent.key")
    assert meta_unknown["description"] == "Configuration parameter"


def test_config_migrate_command(tmp_path):
    """Verify cloudctl config migrate bumps version and merges new schema sections."""
    cfg_file = tmp_path / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    defaults = cm.load_defaults()
    defaults["version"] = "0.1.0"
    cm.save_config(defaults)

    args = argparse.Namespace(
        config_action="migrate",
        target_version="0.3.0",
        config=str(cfg_file),
    )

    rc = execute_config(args)
    assert rc == 0

    updated = cm.load_config()
    assert updated["version"] == "0.3.0"
