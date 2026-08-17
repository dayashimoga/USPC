import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudctl.core.detect import detect_firewall, detect_virtualization
from cloudctl.core.security import SecurityChecker
from src.media.auth import authenticate_request
from src.media.config import MediaConfig


def test_detect_firewalls_mocked():
    with (
        patch(
            "shutil.which",
            side_effect=lambda cmd: "/usr/bin/" + cmd if cmd in ("ufw", "pfctl") else None,
        ),
        patch("cloudctl.core.detect.run_command") as mock_run,
    ):
        mock_run.return_value = MagicMock(success=True, stdout="Status: active")
        fw, active = detect_firewall("linux")
        assert fw == "ufw"
        assert active is True

        mock_run.return_value = MagicMock(success=True, stdout="Status: Enabled")
        fw_mac, active_mac = detect_firewall("macos")
        assert fw_mac == "pf"
        assert active_mac is True


def test_detect_virtualization_mocked():
    with patch("cloudctl.core.detect.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="kvm")
        virt = detect_virtualization("linux")
        assert virt in ("kvm", "native", "wsl2")


def test_security_checker_all_branches(mock_config_dict: dict, temp_dir: Path):
    checker = SecurityChecker(mock_config_dict, temp_dir)

    # Permissions on unix
    sec_dir = Path("~/.uspc/secrets").expanduser().resolve()
    sec_dir.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        sec_dir.chmod(0o700)
    res_perm = checker.check_secret_permissions()
    assert res_perm.status in ("PASS", "FAIL")

    # Public mode check
    mock_config_dict["network"]["mode"] = "public"
    checker_pub = SecurityChecker(mock_config_dict, temp_dir)
    res_pub = checker_pub.check_exposed_ports()
    assert res_pub.status == "WARN"

    res_tls = checker_pub.check_tls_configuration()
    assert res_tls.status == "FAIL"

    # Generic admin user check
    mock_config_dict["cloud"]["admin_user"] = "root"
    checker_root = SecurityChecker(mock_config_dict, temp_dir)
    res_ent = checker_root.check_password_entropy()
    assert res_ent.status == "WARN"


@pytest.mark.asyncio
async def test_auth_and_bearer_middleware(temp_dir: Path):
    cfg = MediaConfig(jwt_secret="super-secret-token-12345")

    req_mock = MagicMock()
    req_mock.app.state.config = cfg
    req_mock.path_params = {"id": "item1"}

    from src.media.auth import create_media_token

    token = create_media_token("item1", cfg.jwt_secret)

    assert authenticate_request(req_mock, auth_header=None, token=token) is True


def test_storage_manager_validation_and_errors(temp_dir: Path):
    from cloudctl.core.storage import StorageManager

    sm = StorageManager(
        data_path=temp_dir / "data", config_path=temp_dir / "config", min_free_space_gb=0.1
    )
    paths = sm.initialize_storage()
    assert paths.base_data.exists()
    assert sm.verify_read_write(paths.base_data) is True

    # Migrate data test
    target_data = temp_dir / "new_data"
    assert sm.migrate_data(target_data) is True
    assert target_data.exists()
