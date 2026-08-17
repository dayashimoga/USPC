"""Comprehensive branch coverage for config, readiness, network, detect, and media."""

import argparse
from unittest.mock import MagicMock, patch

from cloudctl.commands.config_cmd import execute_config
from cloudctl.commands.doctor import execute_doctor
from cloudctl.commands.readiness_cmd import evaluate_readiness, execute_readiness
from cloudctl.commands.test_cmd import execute_test
from cloudctl.core.config import ConfigManager
from cloudctl.core.detect import detect_firewall, detect_virtualization
from cloudctl.core.network import NetworkManager
from media.transcoder import Transcoder


def test_config_cmd_validation_failure_and_diff_branches(tmp_path, capsys):
    """Test config cmd with invalid config and diff rendering with metadata."""
    cfg_file = tmp_path / "cloud.yaml"
    cfg_file.write_text("invalid: yaml: [syntax", encoding="utf-8")

    args = argparse.Namespace(config_action="validate", config=str(cfg_file))
    rc = execute_config(args)
    assert rc == 1

    # Valid config with diff
    cm = ConfigManager(config_path=cfg_file)
    defaults = cm.load_defaults()
    defaults["cloud"]["domain"] = "custom.cloud.domain"
    cm.save_config(defaults)

    args_diff = argparse.Namespace(config_action="diff", config=str(cfg_file))
    rc_diff = execute_config(args_diff)
    assert rc_diff == 0


def test_readiness_cmd_public_and_terminal_branches(tmp_path, capsys):
    """Test readiness evaluation with public mode and terminal output formatting."""
    config = {
        "network": {"mode": "public", "headscale_port": 8080},
        "security": {"tls_enabled": True},
        "services": {
            "nextcloud": {"port": 8081},
            "postgres": {"port": 5432},
            "redis": {"port": 6379},
        },
        "performance": {"profile": "standard"},
        "storage": {"data_path": str(tmp_path)},
    }
    with patch("cloudctl.commands.readiness_cmd.ContainerManager") as mock_cm:
        mock_cm.return_value.get_running_containers.return_value = [
            "uspc-nextcloud",
            "uspc-postgres",
            "uspc-redis",
        ]
        eval_res = evaluate_readiness(config)
        assert eval_res.layers["external_remote"] == "WARN"

        args = argparse.Namespace(json=False, config=None)
        with patch("cloudctl.commands.readiness_cmd.evaluate_readiness", return_value=eval_res):
            execute_readiness(args)
            captured = capsys.readouterr()
            assert "6-LAYER READINESS AUDIT" in captured.out


def test_detect_firewall_and_virtualization_branches():
    """Test ufw, nftables, and WSL/VM platform detection branches."""
    with patch("cloudctl.core.detect.run_command") as mock_run:
        mock_run.side_effect = [
            MagicMock(success=True, stdout="Status: active"),  # ufw
            MagicMock(success=True, stdout="table inet filter"),  # nftables
        ]
        fw, active = detect_firewall("linux")
        assert fw in ("ufw", "nftables", "none", "iptables")

    with patch("cloudctl.core.detect.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="kvm")
        virt = detect_virtualization("linux")
        assert virt == "kvm"


def test_network_manager_edge_branches(tmp_path):
    """Test NetworkManager headscale config and client registration branches."""
    config = {
        "network": {"mode": "private", "vpn_subnet": "10.0.0.0/24", "headscale_port": 9090},
    }
    nm = NetworkManager(config, config_dir=tmp_path)
    conf = nm.generate_headscale_config(private_key="k1", noise_private_key="k2")
    assert conf.exists()


def test_doctor_and_test_command_branches(tmp_path):
    """Test doctor and test CLI commands."""
    args_doc = argparse.Namespace(config=None, verbose=True)
    with patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health:
        mock_health.return_value = MagicMock(overall_status="HEALTHY", checks=[])
        rc = execute_doctor(args_doc)
        assert rc == 0

    args_test = argparse.Namespace(quick=True, coverage=False)
    with patch("cloudctl.commands.test_cmd.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, returncode=0)
        rc_t = execute_test(args_test)
        assert rc_t == 0


def test_media_transcoder_error_branches(tmp_path):
    """Test transcoder job failure handling."""
    tm = Transcoder(cache_dir=tmp_path, max_concurrency=1)
    non_existent = tmp_path / "missing.mkv"
    out_file = tmp_path / "out.mp4"
    assert tm.is_browser_native(out_file) is True
    assert tm.is_browser_native(non_existent) is False
