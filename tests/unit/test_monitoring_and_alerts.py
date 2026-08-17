"""Unit tests for Prometheus metrics formatter, monitor dashboard, alerts, and SBOM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from cloudctl.commands.alerts import execute_alerts_cmd
from cloudctl.commands.monitor import execute_monitor_cmd, render_ascii_dashboard
from cloudctl.commands.sbom_cmd import execute_sbom_cmd
from cloudctl.core.metrics import MetricSnapshot, format_prometheus_metrics


def test_format_prometheus_metrics_output():
    snap = MetricSnapshot(
        timestamp=1700000000.0,
        cpu_percent=42.5,
        ram_percent=65.2,
        disk_free_gb=120.4,
        active_streams=3,
        queue_depth=1,
        error_count=0,
    )
    extra = {"custom_gauge": 100.0}
    prom_text = format_prometheus_metrics(snap, extra_gauges=extra)

    assert "uspc_cpu_utilization_percent 42.50" in prom_text
    assert "uspc_memory_utilization_percent 65.20" in prom_text
    assert "uspc_disk_free_gigabytes 120.40" in prom_text
    assert "uspc_active_streams 3" in prom_text
    assert "uspc_transcoder_queue_depth 1" in prom_text
    assert "uspc_errors_total 0" in prom_text
    assert "uspc_custom_gauge 100.0" in prom_text


def test_render_ascii_dashboard():
    snap = MetricSnapshot(
        timestamp=1700000000.0,
        cpu_percent=15.0,
        ram_percent=30.0,
        disk_free_gb=50.0,
        active_streams=1,
        queue_depth=0,
        error_count=0,
    )
    summary = {"avg_cpu": 12.0, "avg_ram": 28.0, "min_disk_free_gb": 48.0, "peak_streams": 2}
    dashboard = render_ascii_dashboard(snap, summary, alerts=[])
    assert "CPU Load" in dashboard
    assert "RAM Memory" in dashboard
    assert "HEALTHY" in dashboard


def test_execute_monitor_cmd_modes(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # Text mode
    args_text = argparse.Namespace(
        config=str(cfg_file), count=1, interval=0.01, json=False, prometheus=False
    )
    assert execute_monitor_cmd(args_text) == 0

    # JSON mode
    args_json = argparse.Namespace(
        config=str(cfg_file), count=1, interval=0.01, json=True, prometheus=False
    )
    assert execute_monitor_cmd(args_json) == 0

    # Prometheus mode
    args_prom = argparse.Namespace(
        config=str(cfg_file), count=1, interval=0.01, json=False, prometheus=True
    )
    assert execute_monitor_cmd(args_prom) == 0


def test_execute_alerts_cmd_modes(temp_dir: Path):
    # No alerts
    with patch("cloudctl.core.metrics.MetricsStore.check_alerts", return_value=[]):
        args_clean = argparse.Namespace(json=False, fail_on_critical=False)
        assert execute_alerts_cmd(args_clean) == 0

    # Warning alert
    with patch(
        "cloudctl.core.metrics.MetricsStore.check_alerts", return_value=["WARNING: High CPU"]
    ):
        args_warn = argparse.Namespace(json=False, fail_on_critical=False)
        assert execute_alerts_cmd(args_warn) == 1

        args_warn_json = argparse.Namespace(json=True, fail_on_critical=False)
        assert execute_alerts_cmd(args_warn_json) == 1

    # Critical alert with fail-on-critical
    with patch(
        "cloudctl.core.metrics.MetricsStore.check_alerts", return_value=["CRITICAL: CPU 98%"]
    ):
        args_crit = argparse.Namespace(json=False, fail_on_critical=True)
        assert execute_alerts_cmd(args_crit) == 2


def test_execute_sbom_cmd_modes(temp_dir: Path):
    # Text table mode
    args_text = argparse.Namespace(format="text", output=None, json=False, audit=False)
    assert execute_sbom_cmd(args_text) == 0

    # JSON mode to stdout
    args_json = argparse.Namespace(format="json", output=None, json=True, audit=False)
    assert execute_sbom_cmd(args_json) == 0

    # CycloneDX 1.5 mode
    cdx_file = temp_dir / "sbom-cdx.json"
    args_cdx = argparse.Namespace(format="cyclonedx", output=str(cdx_file), json=False, audit=False)
    assert execute_sbom_cmd(args_cdx) == 0
    assert cdx_file.exists()
    cdx_parsed = json.loads(cdx_file.read_text(encoding="utf-8"))
    assert cdx_parsed["bomFormat"] == "CycloneDX"
    assert cdx_parsed["specVersion"] == "1.5"

    # License audit flag
    args_audit = argparse.Namespace(audit=True)
    assert execute_sbom_cmd(args_audit) == 0

    # Output file (SPDX)
    out_file = temp_dir / "sbom.json"
    args_file = argparse.Namespace(format="json", output=str(out_file), json=True, audit=False)
    assert execute_sbom_cmd(args_file) == 0
    assert out_file.exists()

    sbom_parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert sbom_parsed["spdxVersion"] == "SPDX-2.3"
    assert len(sbom_parsed["packages"]) >= 15


def test_monitor_and_alerts_profiles(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # Monitor with STANDARD profile (tests IO and Network lines)
    args_std = argparse.Namespace(
        config=str(cfg_file),
        count=1,
        interval=0.01,
        json=False,
        prometheus=False,
        profile="standard",
    )
    assert execute_monitor_cmd(args_std) == 0

    # Alerts with CLUSTER profile
    with patch("cloudctl.core.metrics.MetricsStore.check_alerts", return_value=[]):
        args_alerts_clust = argparse.Namespace(
            json=False, fail_on_critical=False, profile="cluster"
        )
        assert execute_alerts_cmd(args_alerts_clust) == 0
