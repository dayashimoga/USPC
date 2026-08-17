"""Performance inspection command."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from cloudctl.core.config import ConfigManager
from cloudctl.core.performance import collect_live_metrics, detect_resource_profile


def execute_performance(args: argparse.Namespace) -> int:
    """Execute live system performance metrics display."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()

    profile = detect_resource_profile(config.get("performance", {}).get("profile", "auto"))
    data_path = config.get("storage", {}).get("data_path", "~/.uspc/data")
    metrics = collect_live_metrics(data_path)

    if getattr(args, "json", False):
        payload = {
            "resource_profile": asdict(profile),
            "metrics": asdict(metrics),
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("\n" + "=" * 70)
    print(" USPC Live Performance & Capacity Monitor")
    print("=" * 70)
    print(f" Resource Profile   : [{profile.name}] - {profile.description}")
    print(f" CPU Utilization    : {metrics.cpu_percent:.1f}%")
    print(
        f" Memory Usage       : {metrics.ram_percent:.1f}% ({metrics.ram_used_gb:.1f} GB / {metrics.ram_total_gb:.1f} GB)"
    )
    print(
        f" Free Storage Space : {metrics.disk_free_gb:.1f} GB ({100 - metrics.disk_used_percent:.1f}% free)"
    )
    print(f" Active Streams     : {metrics.active_streams} / {profile.max_concurrent_streams}")
    print(f" Health State       : [{metrics.status}]")

    if metrics.bottlenecks:
        print("\n Detected Bottlenecks:")
        for b in metrics.bottlenecks:
            print(f"  [!] {b}")
    else:
        print("\n System Bottlenecks : None detected (Capacity is balanced)")

    print("=" * 70 + "\n")
    return 0
