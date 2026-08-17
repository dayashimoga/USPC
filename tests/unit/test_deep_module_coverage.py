"""Deep branch coverage test suite targeting >95% overall repository coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudctl.commands.init import execute_init
from cloudctl.commands.lifecycle import execute_restart, execute_start, execute_stop
from cloudctl.commands.test_cmd import execute_test
from cloudctl.core.config import ConfigManager, get_repo_root, load_yaml
from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import (
    detect_container_engine,
    detect_disks,
    detect_firewall,
    detect_host,
    detect_os,
    detect_privileges,
    detect_virtualization,
)
from cloudctl.utils.fs import atomic_write, get_total_disk_space_gb, remove_path_safely
from src.media.metadata import MetadataExtractor, detect_media_type_and_mime
from src.media.thumbnails import ThumbnailGenerator


def test_detect_comprehensive():
    os_name, rel, ver, arch = detect_os()
    assert os_name in ("linux", "windows", "macos")

    # detect_privileges
    assert isinstance(detect_privileges(os_name), bool)
    assert detect_privileges("unknown_os") is False

    # detect_virtualization variants
    with patch("cloudctl.core.detect.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="kvm")
        assert detect_virtualization("linux") == "kvm"

        mock_run.return_value = MagicMock(success=True, stdout="running")
        assert "hyperv" in detect_virtualization("windows") or "native" in detect_virtualization(
            "windows"
        )
        assert detect_virtualization("macos") == "native-macos"
        assert detect_virtualization("other") == "unknown"

    # detect_container_engine
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        eng, ver = detect_container_engine()
        assert eng == "none"

    # detect_firewall variants
    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda x: "/usr/bin/ufw" if x == "ufw" else None
        with patch("cloudctl.core.detect.run_command") as mock_run:
            mock_run.return_value = MagicMock(success=True, stdout="Status: active")
            fw, act = detect_firewall("linux")
            assert fw == "ufw"
            assert act is True

        # firewalld branch
        mock_which.side_effect = lambda x: "/usr/bin/firewall-cmd" if x == "firewall-cmd" else None
        with patch("cloudctl.core.detect.run_command") as mock_run:
            mock_run.return_value = MagicMock(success=True, stdout="running")
            fw, act = detect_firewall("linux")
            assert fw == "firewalld"

        # iptables branch
        mock_which.side_effect = lambda x: "/usr/bin/iptables" if x == "iptables" else None
        fw, act = detect_firewall("linux")
        assert fw == "iptables"

        # none branch
        mock_which.side_effect = lambda x: None
        fw, act = detect_firewall("linux")
        assert fw == "none"

    # detect_disks
    disks = detect_disks()
    assert isinstance(disks, list)

    # detect_host
    host = detect_host()
    assert host.cpu_cores >= 1
    assert host.total_ram_gb > 0


def test_container_manager_deep_branches():
    cm = ContainerManager(engine="docker")

    # get_version
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="Docker version 25.0.0\n")
        assert "Docker" in cm.get_version()

        mock_run.return_value = MagicMock(success=False, stdout="")
        assert cm.get_version() == "unknown"

    # start, restart, stop, remove
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="")
        assert cm.start_container("test-c") is True
        assert cm.restart_container("test-c") is True
        assert cm.stop_container("test-c") is True
        assert cm.remove_container("test-c") is True

    # inspect container parse error
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="invalid_json_output")
        assert cm.inspect_container("test-c") is None

    # exec command string vs sequence
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="executed")
        assert cm.exec_command("test-c", "ls -la", user="root").success is True
        assert cm.exec_command("test-c", ["ls", "-la"]).success is True

    # get_logs
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="log line 1\n", stderr="")
        assert "log line 1" in cm.get_logs("test-c")


def test_metadata_and_thumbnails_deep(temp_dir: Path):
    # detect_media_type_and_mime extensions
    f_avi = temp_dir / "test.avi"
    assert detect_media_type_and_mime(f_avi)[0] == "video"
    f_flac = temp_dir / "test.flac"
    assert detect_media_type_and_mime(f_flac)[0] == "audio"
    f_bmp = temp_dir / "test.bmp"
    assert detect_media_type_and_mime(f_bmp)[0] == "image"
    f_bin = temp_dir / "test.bin"
    assert detect_media_type_and_mime(f_bin)[0] == "unknown"

    # Metadata extractor with invalid ffprobe output
    extractor = MetadataExtractor()
    extractor.ffprobe_path = "/usr/bin/ffprobe"
    with patch("src.media.metadata.run_command") as mock_run:
        # Invalid JSON
        mock_run.return_value = MagicMock(success=True, stdout="not_json")
        meta = extractor.extract(f_avi)
        assert meta.media_type == "video"

    # Thumbnail generator fallback badge
    tg = ThumbnailGenerator(temp_dir / "thumbs", default_width=200)
    badge_path = tg.generate(temp_dir / "document.pdf", "doc1", "unknown")
    assert badge_path is not None
    assert badge_path.exists()


def test_config_manager_error_branches(temp_dir: Path):
    cm = ConfigManager(config_path=temp_dir / "non_existing.yaml", repo_root=temp_dir)
    assert get_repo_root() is not None

    # Load non existing yaml directly
    with pytest.raises(FileNotFoundError):
        load_yaml(temp_dir / "really_not_there.yaml")

    # Port collision validation
    invalid_cfg = {
        "network": {"vpn_subnet": "100.64.0.0/10", "headscale_port": 8080},
        "services": {
            "s1": {"port": 8080},
            "s2": {"port": 8080},
        },
        "media": {"enabled": True, "port": 8085},
    }
    with patch.object(cm, "load_schema", return_value={"type": "object"}):
        with pytest.raises(ValueError) as exc:
            cm.validate(invalid_cfg)
        assert "Port collision" in str(exc.value)


def test_fs_utilities_deep(temp_dir: Path):
    # atomic write binary
    bin_file = temp_dir / "atomic_bin.dat"
    atomic_write(bin_file, b"BINARY_DATA_PAYLOAD", mode=0o644)
    assert bin_file.read_bytes() == b"BINARY_DATA_PAYLOAD"

    # get_total_disk_space_gb
    total_gb = get_total_disk_space_gb(temp_dir)
    assert total_gb > 0

    # remove_path_safely
    assert remove_path_safely(temp_dir / "non_existent_file.xyz") is False
    test_d = temp_dir / "dir_to_remove"
    test_d.mkdir()
    (test_d / "file.txt").write_text("hello", encoding="utf-8")
    assert remove_path_safely(test_d) is True
    assert not test_d.exists()


def test_cli_lifecycle_and_test_commands():
    # execute_start, execute_stop, execute_restart
    args = MagicMock(config=None)
    with (
        patch("cloudctl.core.container.ContainerManager.start_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.stop_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.restart_container", return_value=True),
    ):
        assert execute_start(args) == 0
        assert execute_stop(args) == 0
        assert execute_restart(args) == 0

    # execute_init
    init_args = MagicMock(config=None, force=False, name="newcloud", domain="newcloud.local")
    with (
        patch("cloudctl.core.config.ConfigManager.save_config"),
        patch("cloudctl.core.secrets.SecretManager.load_or_generate_secrets"),
    ):
        assert execute_init(init_args) == 0

    # execute_test command
    test_args = MagicMock(media_only=True, coverage=True)
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        assert execute_test(test_args) == 0
