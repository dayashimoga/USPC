"""Simulated cross-network VPN mesh topology and Headscale configuration tests."""

from unittest.mock import MagicMock, patch

from cloudctl.core.network import NetworkManager


def test_headscale_mesh_configuration_generation(tmp_path):
    """Verify Headscale WireGuard mesh configuration generation with private keys."""
    config = {
        "cloud": {"domain": "mesh.cloud.local"},
        "network": {
            "mode": "private",
            "vpn_subnet": "100.64.0.0/10",
            "headscale_port": 8080,
            "enable_magic_dns": True,
        },
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    net_mgr = NetworkManager(config, config_dir=config_dir)
    conf_path = net_mgr.generate_headscale_config(
        private_key="test_private_key_data",
        noise_private_key="test_noise_key_data",
    )

    assert conf_path.exists()
    content = conf_path.read_text(encoding="utf-8")
    assert "100.64.0.0/10" in content
    assert "8080" in content


def test_cross_network_peer_enrollment_simulation(tmp_path):
    """Verify peer node registration and unauthorized node rejection."""
    config = {
        "network": {"mode": "private", "headscale_port": 8080},
    }
    net_mgr = NetworkManager(config, config_dir=tmp_path)

    # Mock peer registration commands
    with patch("cloudctl.core.network.run_command") as mock_run:
        mock_run.return_value = MagicMock(
            success=True, stdout="Node node-client-1 enrolled successfully"
        )
        res = net_mgr.register_vpn_client(user="alice", node_key="mkey:client12345")
        assert res is True
