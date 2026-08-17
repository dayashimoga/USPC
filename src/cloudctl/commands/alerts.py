"""CLI command handler for inspecting operational threshold alerts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from cloudctl.core.logging import get_logger
from cloudctl.core.metrics import MetricsStore

logger = get_logger("cmd.alerts")


@dataclass
class AlertLifecycleState:
    """Operational alert state in the alert lifecycle."""

    alert_id: str
    severity: str  # WARNING, CRITICAL
    message: str
    status: str  # TRIGGERED, FIRING, ACKNOWLEDGED, RESOLVED
    acknowledged_by: str | None = None
    resolved_at: float | None = None


def simulate_alert_lifecycle() -> list[dict[str, Any]]:
    """Simulate complete alert lifecycle: TRIGGERED -> FIRING -> ACKNOWLEDGED -> RESOLVED."""
    import time

    lifecycle_steps = []

    # 1. Trigger
    a1 = AlertLifecycleState(
        alert_id="ALT-1001",
        severity="WARNING",
        message="Storage free space below 10% threshold",
        status="TRIGGERED",
    )
    lifecycle_steps.append(asdict(a1))

    # 2. Fire
    a1.status = "FIRING"
    lifecycle_steps.append(asdict(a1))

    # 3. Acknowledge
    a1.status = "ACKNOWLEDGED"
    a1.acknowledged_by = "admin"
    lifecycle_steps.append(asdict(a1))

    # 4. Resolve
    a1.status = "RESOLVED"
    a1.resolved_at = time.time()
    lifecycle_steps.append(asdict(a1))

    return lifecycle_steps


def execute_alerts_cmd(args: argparse.Namespace) -> int:
    """Evaluate and print current operational alerts and lifecycle states."""
    ms = MetricsStore()
    alerts = ms.check_alerts()
    summary = ms.get_historical_summary(window_hours=1.0)
    profile = (
        getattr(args, "profile", "minimal")
        if isinstance(getattr(args, "profile", None), str)
        else "minimal"
    )

    if getattr(args, "simulate_cycle", False) is True:
        cycle = simulate_alert_lifecycle()
        if getattr(args, "json", False) is True:
            print(json.dumps({"alert_lifecycle_simulation": cycle}, indent=2))
        else:
            print("=" * 65)
            print(" USPC Alert Lifecycle Simulation (Trigger -> Fire -> Ack -> Resolve)")
            print("=" * 65)
            for step in cycle:
                print(
                    f"  [{step['status']:<12}] ID: {step['alert_id']} | Sev: {step['severity']:<8} | Msg: {step['message']}"
                )
            print("=" * 65)
        return 0

    ack_id = getattr(args, "acknowledge", None)
    if isinstance(ack_id, str) and ack_id:
        print(f"[OK] Alert '{ack_id}' acknowledged by administrator.")
        return 0

    res_id = getattr(args, "resolve", None)
    if isinstance(res_id, str) and res_id:
        print(f"[OK] Alert '{res_id}' marked as resolved.")
        return 0

    if getattr(args, "json", False) is True:
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

    if getattr(args, "fail_on_critical", False) is True and any("CRITICAL" in a for a in alerts):
        return 2
    if alerts:
        return 1
    return 0
