"""WireGuard and self-hosted Headscale mesh networking management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import atomic_write, ensure_directory

logger = get_logger("network")


@dataclass
class PortRule:
    """Port firewall specification."""

    port: int
    protocol: str  # tcp, udp
    description: str
    access: str  # vpn-only, public, localhost-only


from cloudctl.utils.shell import run_command


class NetworkManager:
    """Manages Headscale coordination, WireGuard tunnels, and port firewall policies."""

    def __init__(self, config: dict[str, Any], config_dir: str | Path | None = None):
        self.config = config
        self.config_dir = (
            Path(config_dir).expanduser().resolve()
            if config_dir
            else Path("~/.uspc/config").expanduser().resolve()
        )
        self.net_config = config.get("network", {})
        self.mode = self.net_config.get("mode", "private")
        self.vpn_subnet = self.net_config.get("vpn_subnet", "100.64.0.0/10")
        self.headscale_port = self.net_config.get("headscale_port", 8080)

    def register_vpn_client(self, user: str, node_key: str) -> bool:
        """Enroll a new client node into the Headscale mesh network."""
        cmd = ["headscale", "nodes", "register", "--user", user, "--key", node_key]
        res = run_command(cmd, timeout=30.0)
        return res.success

    def get_port_matrix(self) -> list[PortRule]:
        """Return the documented port matrix for the current configuration."""
        rules = [
            PortRule(
                port=self.headscale_port,
                protocol="tcp",
                description="Headscale VPN control",
                access="public" if self.mode == "public" else "vpn-only",
            ),
            PortRule(
                port=5432, protocol="tcp", description="PostgreSQL DB", access="localhost-only"
            ),
            PortRule(port=6379, protocol="tcp", description="Redis Cache", access="localhost-only"),
            PortRule(port=8081, protocol="tcp", description="Nextcloud Web", access="vpn-only"),
            PortRule(
                port=8085,
                protocol="tcp",
                description="USPC Media Streaming API & Web",
                access="vpn-only",
            ),
        ]
        if self.mode == "public":
            rules.append(
                PortRule(
                    port=80,
                    protocol="tcp",
                    description="HTTP Reverse Proxy (Caddy)",
                    access="public",
                )
            )
            rules.append(
                PortRule(
                    port=443,
                    protocol="tcp",
                    description="HTTPS Reverse Proxy (Caddy)",
                    access="public",
                )
            )
        return rules

    def generate_headscale_config(self, private_key: str, noise_private_key: str) -> Path:
        """Generate Headscale YAML configuration file."""
        headscale_dir = self.config_dir / "headscale"
        ensure_directory(headscale_dir, mode=0o750)
        config_file = headscale_dir / "config.yaml"

        headscale_conf = {
            "server_url": f"http://127.0.0.1:{self.headscale_port}",
            "listen_addr": f"0.0.0.0:{self.headscale_port}",
            "metrics_listen_addr": "127.0.0.1:9090",
            "grpc_listen_addr": "127.0.0.1:50443",
            "grpc_allow_insecure": False,
            "private_key_path": str(headscale_dir / "private.key"),
            "noise": {
                "private_key_path": str(headscale_dir / "noise_private.key"),
            },
            "prefixes": {
                "v4": self.vpn_subnet,
                "v6": "fd7a:115c:a1e0::/48",
            },
            "derp": {
                "server": {
                    "enabled": False,
                },
                "urls": [],
                "paths": [],
                "auto_update_enabled": False,
                "update_frequency": "24h",
            },
            "disable_check_updates": True,
            "ephemeral_node_inactivity_timeout": "30m",
            "database": {
                "type": "sqlite3",
                "sqlite": {
                    "path": str(headscale_dir / "db.sqlite"),
                },
            },
            "dns": {
                "magic_dns": self.net_config.get("enable_magic_dns", True),
                "base_domain": "uspc.net",
                "nameservers": ["1.1.1.1", "9.9.9.9"],
            },
            "log": {
                "level": "info",
                "format": "text",
            },
        }

        # Save private keys
        atomic_write(headscale_dir / "private.key", private_key, mode=0o600)
        atomic_write(headscale_dir / "noise_private.key", noise_private_key, mode=0o600)
        # Save headscale yaml config
        atomic_write(config_file, yaml.dump(headscale_conf, default_flow_style=False), mode=0o640)
        logger.info(f"Headscale VPN configuration generated at {config_file}")
        return config_file

    def generate_firewall_rules(self, os_name: str) -> list[str]:
        """Generate platform-specific firewall commands to enforce zero-leak policy."""
        commands: list[str] = []
        matrix = self.get_port_matrix()

        if os_name == "linux":
            # UFW rules
            commands.append("ufw default deny incoming")
            commands.append("ufw default allow outgoing")
            for rule in matrix:
                if rule.access == "public":
                    commands.append(
                        f"ufw allow {rule.port}/{rule.protocol} comment '{rule.description}'"
                    )
            commands.append("ufw enable")

        elif os_name == "windows":
            # PowerShell NetFirewallRule
            for rule in matrix:
                if rule.access == "public":
                    commands.append(
                        f"New-NetFirewallRule -DisplayName 'USPC {rule.description}' -Direction Inbound "
                        f"-LocalPort {rule.port} -Protocol {rule.protocol.upper()} -Action Allow"
                    )
        return commands
