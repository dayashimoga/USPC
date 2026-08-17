"""Live terminal monitoring dashboard and telemetry command."""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger
from cloudctl.core.metrics import MetricSnapshot, MetricsStore, format_prometheus_metrics
from cloudctl.core.performance import collect_live_metrics

logger = get_logger("cmd.monitor")


def render_ascii_dashboard(snapshot: Any, summary: dict[str, Any], alerts: list[str]) -> str:
    """Render a clean, high-density terminal dashboard."""
    lines = []
    lines.append("=" * 68)
    lines.append("        USPC OBSERVABILITY & SYSTEM MONITORING DASHBOARD")
    lines.append("=" * 68)

    # CPU bar
    cpu_bars = int(snapshot.cpu_percent / 5)
    cpu_bar_str = "[" + "#" * cpu_bars + " " * (20 - cpu_bars) + "]"
    lines.append(
        f" CPU Load   : {cpu_bar_str} {snapshot.cpu_percent:>5.1f}%  (Avg 1h: {summary.get('avg_cpu', 0):.1f}%)"
    )

    # RAM bar
    ram_bars = int(snapshot.ram_percent / 5)
    ram_bar_str = "[" + "#" * ram_bars + " " * (20 - ram_bars) + "]"
    lines.append(
        f" RAM Memory : {ram_bar_str} {snapshot.ram_percent:>5.1f}%  (Avg 1h: {summary.get('avg_ram', 0):.1f}%)"
    )

    # Storage & Streams
    lines.append(
        f" Disk Free  : {snapshot.disk_free_gb:>6.1f} GB free  | Min 1h: {summary.get('min_disk_free_gb', 0):.1f} GB"
    )
    lines.append(
        f" Streams    : {snapshot.active_streams:>6} active   | Peak 1h: {summary.get('peak_streams', 0)}"
    )
    lines.append(
        f" Queue Depth: {snapshot.queue_depth:>6} jobs     | Errors: {snapshot.error_count}"
    )
    lines.append("-" * 68)

    # Health & Bottleneck Assessment
    bottlenecks = []
    if snapshot.cpu_percent > 85.0:
        bottlenecks.append("CPU Saturation (>85%)")
    if snapshot.ram_percent > 90.0:
        bottlenecks.append("Memory Pressure (>90%)")
    if snapshot.disk_free_gb < 10.0:
        bottlenecks.append("Low Disk Capacity (<10GB)")

    health_str = "HEALTHY" if not bottlenecks and not alerts else "WARNING / PRESSURE"
    lines.append(f" Operational State: [{health_str}]")
    if bottlenecks:
        lines.append(f" Bottlenecks      : {', '.join(bottlenecks)}")
    else:
        lines.append(" Bottlenecks      : None detected")

    if alerts:
        lines.append("\n Active Alerts:")
        for a in alerts:
            lines.append(f"  ! {a}")
    lines.append("=" * 68)

    return "\n".join(lines)


def execute_monitor_cmd(args: argparse.Namespace) -> int:
    """Execute live monitoring command."""
    cfg_mgr = ConfigManager(config_path=getattr(args, "config", None))
    config = cfg_mgr.load_config()
    ms = MetricsStore()

    count = getattr(args, "count", 1)
    interval = getattr(args, "interval", 2.0)
    as_json = getattr(args, "json", False)
    as_prometheus = getattr(args, "prometheus", False)

    data_path = config.get("storage", {}).get("data_path", "~/.uspc/data")
    for i in range(count):
        live = collect_live_metrics(data_path=data_path)
        snap = MetricSnapshot(
            timestamp=time.time(),
            cpu_percent=live.cpu_percent,
            ram_percent=live.ram_percent,
            disk_free_gb=live.disk_free_gb,
            active_streams=live.active_streams,
            queue_depth=live.queue_depth,
            error_count=0,
        )
        ms.record_snapshot(snap)

        summary = ms.get_historical_summary(window_hours=1.0)
        alerts = ms.check_alerts()

        if as_prometheus:
            prom_text = format_prometheus_metrics(snap)
            print(prom_text)
        elif as_json:
            data = {
                "timestamp": snap.timestamp,
                "current": snap.__dict__,
                "summary_1h": summary,
                "alerts": alerts,
            }
            print(json.dumps(data, indent=2))
        else:
            dashboard = render_ascii_dashboard(snap, summary, alerts)
            print(dashboard)

        if i < count - 1:
            time.sleep(interval)

    return 0
