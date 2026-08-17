"""CLI command handler for inspecting operational threshold alerts."""

from __future__ import annotations

import argparse
import json

from cloudctl.core.logging import get_logger
from cloudctl.core.metrics import MetricsStore

logger = get_logger("cmd.alerts")


def execute_alerts_cmd(args: argparse.Namespace) -> int:
    """Evaluate and print current operational alerts."""
    ms = MetricsStore()
    alerts = ms.check_alerts()
    summary = ms.get_historical_summary(window_hours=1.0)
    profile = getattr(args, "profile", "minimal")

    if getattr(args, "json", False):
        data = {
            "profile": profile,
            "alert_count": len(alerts),
            "alerts": alerts,
            "recent_summary": summary,
        }
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print(f" USPC Operational Threshold Alerts [{profile.upper()}]")
        print("=" * 60)
        if alerts:
            for idx, a in enumerate(alerts, 1):
                print(f" [{idx}] {a}")
        else:
            print(" [OK] No active alert threshold violations.")
        print("-" * 60)
        print(
            f" Samples (1h): {summary.get('sample_count', 0)} | Peak CPU: {summary.get('max_cpu', 0)}% | Peak RAM: {summary.get('max_ram', 0)}%"
        )
        print("=" * 60)

    if getattr(args, "fail_on_critical", False) and any("CRITICAL" in a for a in alerts):
        return 2
    if alerts:
        return 1
    return 0
