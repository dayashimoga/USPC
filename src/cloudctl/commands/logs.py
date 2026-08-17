"""Logs command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager


def execute_logs(args: argparse.Namespace) -> int:
    """Display container logs."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    cm = ContainerManager(config["runtime"]["engine"])

    target_svc = getattr(args, "service", None)
    tail = getattr(args, "tail", 100)

    if target_svc:
        svc_name = f"uspc-{target_svc}" if not target_svc.startswith("uspc-") else target_svc
        logs = cm.get_logs(svc_name, tail=tail)
        print(f"\n--- Logs for {svc_name} (Last {tail} lines) ---")
        print(logs or "[No logs available]")
        print("-------------------------------------------------\n")
    else:
        services = ["uspc-nextcloud", "uspc-media", "uspc-postgres", "uspc-redis", "uspc-headscale"]
        for s in services:
            logs = cm.get_logs(s, tail=20)
            print(f"\n--- Logs for {s} ---")
            print(logs or "[No logs]")
    return 0
