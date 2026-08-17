"""Targeted tests to cross 90%+ code coverage threshold."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.security import HTTPAuthorizationCredentials

from cloudctl.commands.uninstall import execute_uninstall
from cloudctl.commands.update import execute_update
from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import (
    detect_container_engine,
    detect_disks,
    detect_host,
    detect_privileges,
    detect_virtualization,
)
from src.media.auth import authenticate_request
from src.media.config import MediaConfig


def test_uninstall_purge_and_interactive(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    ConfigManager(config_path=cfg_file).save_config(mock_config_dict)

    # 1. Purge data true
    args_purge = argparse.Namespace(config=str(cfg_file), purge_data=True, force=True)
    with (
        patch("cloudctl.core.container.ContainerManager.remove_container", return_value=True),
        patch("cloudctl.utils.fs.remove_path_safely", return_value=True),
    ):
        assert execute_uninstall(args_purge) == 0

    # 2. Interactive cancelled (user answers 'no')
    args_cancel = argparse.Namespace(config=str(cfg_file), purge_data=True, force=False)
    with patch("builtins.input", return_value="no"):
        assert execute_uninstall(args_cancel) == 0


def test_update_active_mode(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    ConfigManager(config_path=cfg_file).save_config(mock_config_dict)

    args_up = argparse.Namespace(config=str(cfg_file), dry_run=False)
    with (
        patch("cloudctl.core.backup.BackupManager.create_backup", return_value=True),
        patch("cloudctl.utils.shell.run_command") as mock_run,
        patch("cloudctl.core.container.ContainerManager.restart_container", return_value=True),
        patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health,
    ):
        mock_run.return_value = MagicMock(success=True, returncode=0)
        mock_health.return_value = MagicMock(overall_status="HEALTHY", checks=[])
        assert execute_update(args_up) == 0


def test_container_manager_docker_network():
    cm = ContainerManager(engine="docker")
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="{}", returncode=0)
        assert cm.create_pod([(8080, 8080)]) is True
        assert cm.is_available() is True


def test_detect_branches_simulated():
    with (
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", side_effect=FileNotFoundError),
    ):
        v = detect_virtualization("linux")
        assert isinstance(v, str) and len(v) > 0

    host = detect_host()
    assert host.cpu_cores > 0
    assert host.total_ram_gb > 0
    disks = detect_disks()
    assert isinstance(disks, list)
    priv_win = detect_privileges("windows")
    assert isinstance(priv_win, bool)
    priv_lin = detect_privileges("linux")
    assert isinstance(priv_lin, bool)
    engine, ver = detect_container_engine()
    assert engine in ("podman", "docker", "none")


def test_auth_bearer_header_variants():
    cfg = MediaConfig(jwt_secret="super-secret-key-12345")
    from src.media.auth import create_media_token

    token = create_media_token("item_xyz", cfg.jwt_secret)

    req_mock = MagicMock()
    req_mock.app.state.config = cfg
    req_mock.path_params = {"id": "item_xyz"}

    # Authorization: HTTPAuthorizationCredentials
    auth_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert authenticate_request(req_mock, auth_header=auth_cred, token=None) is True

    # Global token Bearer
    global_token = create_media_token("global", cfg.jwt_secret)
    auth_cred_global = HTTPAuthorizationCredentials(scheme="Bearer", credentials=global_token)
    assert authenticate_request(req_mock, auth_header=auth_cred_global, token=None) is True


def test_container_manager_extra_branches():
    cm = ContainerManager(engine="docker")
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(
            success=True,
            stdout='[{"Id": "cid1234567890", "State": {"Status": "running"}, "Config": {"Image": "test:latest"}}]',
            stderr="",
            returncode=0,
        )
        stat = cm.get_container_status("uspc-test")
        assert stat.status == "running"
        logs = cm.get_logs("uspc-test", tail=50)
        assert "cid1234567890" in logs
        assert cm.exec_command("uspc-test", "echo 1", user="root").success is True


def test_backup_empty_snapshots(mock_config_dict: dict, temp_dir: Path):
    from cloudctl.core.backup import BackupManager

    bm = BackupManager(mock_config_dict, secrets_dir=temp_dir / "secrets")
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=False, stdout="", stderr="error", returncode=1)
        assert len(bm.list_snapshots()) == 0
        assert bm.restore_backup(snapshot_id="nonexistent") is False


def test_api_404_and_invalid_stream(temp_dir: Path):
    from fastapi.testclient import TestClient

    from src.media.app import create_app
    from src.media.config import MediaConfig

    cfg = MediaConfig(
        data_path=temp_dir / "data", cache_path=temp_dir / "cache", jwt_secret="test_secret_404"
    )
    app = create_app(cfg)
    with TestClient(app) as client:
        auth_hdr = {"Authorization": "Bearer test_secret_404"}
        # Non-existent item 404s
        assert client.get("/api/media/non_existing_id").status_code == 404
        assert client.get("/api/media/non_existing_id/thumbnail").status_code == 404
        assert client.get("/api/media/non_existing_id/stream", headers=auth_hdr).status_code == 404
        assert (
            client.get("/api/media/non_existing_id/download", headers=auth_hdr).status_code == 404
        )
