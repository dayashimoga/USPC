"""Unit tests for networking, Headscale config generation, and security checks."""

from pathlib import Path

from cloudctl.core.network import NetworkManager
from cloudctl.core.security import SecurityChecker


def test_network_manager(mock_config_dict: dict, temp_dir: Path):
    cfg_dir = temp_dir / "config"
    nm = NetworkManager(mock_config_dict, cfg_dir)

    matrix = nm.get_port_matrix()
    assert len(matrix) >= 5
    assert any(r.port == 8085 for r in matrix)  # Media port
    assert any(r.port == 8080 for r in matrix)  # Headscale

    # Config generation
    conf_file = nm.generate_headscale_config(
        private_key="dGVzdF9wcml2YXRlX2tleQ==",
        noise_private_key="dGVzdF9ub2lzZV9wcml2YXRlX2tleQ==",
    )
    assert conf_file.exists()
    content = conf_file.read_text(encoding="utf-8")
    assert "100.64.0.0/10" in content

    # Firewall rules
    linux_fw = nm.generate_firewall_rules("linux")
    assert len(linux_fw) > 0

    win_fw = nm.generate_firewall_rules("windows")
    assert isinstance(win_fw, list)


def test_security_checker(mock_config_dict: dict, temp_dir: Path):
    checker = SecurityChecker(mock_config_dict, temp_dir)
    results = checker.run_all_checks()
    assert len(results) >= 5
    assert all(r.status in ("PASS", "WARN", "FAIL") for r in results)
