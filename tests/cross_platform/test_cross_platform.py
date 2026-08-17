"""Cross-platform compatibility and virtualization simulation tests."""

from pathlib import Path

from cloudctl.core.detect import detect_firewall, detect_os, detect_virtualization


def test_cross_platform_detection():
    os_name, release, version, arch = detect_os()
    assert os_name in ("linux", "windows", "macos", "unknown")

    virt = detect_virtualization(os_name)
    assert isinstance(virt, str)

    fw, active = detect_firewall(os_name)
    assert isinstance(fw, str)
    assert isinstance(active, bool)


def test_platform_specific_firewall_matrix(mock_config_dict: dict, temp_dir: Path):
    from cloudctl.core.network import NetworkManager

    nm = NetworkManager(mock_config_dict, temp_dir)

    linux_rules = nm.generate_firewall_rules("linux")
    assert any("ufw default deny incoming" in r for r in linux_rules)

    win_rules = nm.generate_firewall_rules("windows")
    assert isinstance(win_rules, list)
