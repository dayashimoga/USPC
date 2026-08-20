"""Comprehensive unit tests for all cloudctl CLI command handlers."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from cloudctl.commands.backup import execute_backup
from cloudctl.commands.benchmark import execute_benchmark
from cloudctl.commands.bundle import execute_bundle
from cloudctl.commands.doctor import execute_doctor
from cloudctl.commands.lifecycle import execute_restart, execute_start, execute_stop
from cloudctl.commands.logs import execute_logs
from cloudctl.commands.migrate import execute_migrate
from cloudctl.commands.performance_cmd import execute_performance
from cloudctl.commands.restore import execute_restore
from cloudctl.commands.status import execute_status
from cloudctl.commands.test_cmd import execute_test
from cloudctl.commands.uninstall import execute_uninstall
from cloudctl.commands.update import execute_update
from cloudctl.core.config import ConfigManager


def test_command_backup_and_restore(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    # Backup verify
    args_b_ver = argparse.Namespace(config=str(cfg_file), verify=True)
    with patch("cloudctl.core.backup.BackupManager.verify_repository", return_value=True):
        assert execute_backup(args_b_ver) == 0

    # Backup create
    args_b_create = argparse.Namespace(config=str(cfg_file), verify=False, tag="test_tag")
    with patch("cloudctl.core.backup.BackupManager.create_backup", return_value=True):
        assert execute_backup(args_b_create) == 0

    # Restore dry-run
    args_r_dry = argparse.Namespace(
        config=str(cfg_file), test=False, snapshot="latest", dry_run=True
    )
    with patch("cloudctl.core.backup.BackupManager.restore_backup", return_value=True):
        assert execute_restore(args_r_dry) == 0

    # Restore test isolation
    args_r_test = argparse.Namespace(config=str(cfg_file), test=True)
    with patch("cloudctl.core.backup.BackupManager.test_restore_isolation", return_value=True):
        assert execute_restore(args_r_test) == 0


def test_command_performance_and_benchmark(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    # Performance
    args_p = argparse.Namespace(config=str(cfg_file), json=False)
    assert execute_performance(args_p) == 0

    args_p_json = argparse.Namespace(config=str(cfg_file), json=True)
    assert execute_performance(args_p_json) == 0

    # Benchmark
    args_bm = argparse.Namespace(config=str(cfg_file), profile="SMALL", json=False)
    assert execute_benchmark(args_bm) == 0

    args_bm_json = argparse.Namespace(config=str(cfg_file), profile="SMALL", json=True)
    assert execute_benchmark(args_bm_json) == 0


def test_command_lifecycle(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    args = argparse.Namespace(config=str(cfg_file))
    with (
        patch(
            "cloudctl.core.container.ContainerManager.inspect_container",
            return_value={"id": "mock_id"},
        ),
        patch("cloudctl.core.container.ContainerManager.start_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.stop_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.restart_container", return_value=True),
    ):
        assert execute_start(args) == 0
        assert execute_stop(args) == 0
        assert execute_restart(args) == 0


def test_command_status_and_doctor(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    args_s = argparse.Namespace(config=str(cfg_file), json=False)
    execute_status(args_s)

    args_d = argparse.Namespace(config=str(cfg_file), fix=True)
    execute_doctor(args_d)


def test_command_migrate(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    bundle_out = temp_dir / "mig.tar.gz"
    args_exp = argparse.Namespace(
        config=str(cfg_file), migrate_action="export", output=str(bundle_out)
    )
    assert execute_migrate(args_exp) == 0

    args_imp = argparse.Namespace(
        config=str(cfg_file), migrate_action="import", input=str(bundle_out)
    )
    assert execute_migrate(args_imp) == 0


def test_command_update_and_uninstall(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    args_u = argparse.Namespace(config=str(cfg_file), dry_run=True)
    assert execute_update(args_u) == 0

    args_un = argparse.Namespace(config=str(cfg_file), purge_data=False, force=True)
    assert execute_uninstall(args_un) == 0


def test_command_logs_bundle_and_test(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    # Logs
    args_l1 = argparse.Namespace(config=str(cfg_file), service="media", tail=10)
    assert execute_logs(args_l1) == 0

    args_l2 = argparse.Namespace(config=str(cfg_file), service=None, tail=10)
    assert execute_logs(args_l2) == 0

    # Bundle
    bundle_target = temp_dir / "offline.tar.gz"
    args_b = argparse.Namespace(output=str(bundle_target))
    assert execute_bundle(args_b) == 0
    assert bundle_target.exists()

    # Test runner
    args_t = argparse.Namespace(media_only=True, coverage=False)
    with patch("cloudctl.commands.test_cmd.run_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="test ok", stderr="")
        assert execute_test(args_t) == 0
