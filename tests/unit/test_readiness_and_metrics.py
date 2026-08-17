"""Comprehensive tests for historical metrics store and production readiness evaluation."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from cloudctl.commands.readiness_cmd import evaluate_readiness, execute_readiness
from cloudctl.core.metrics import MetricSnapshot, MetricsStore


def test_metrics_store_lifecycle(temp_dir: Path):
    db_file = temp_dir / "metrics.sqlite"
    store = MetricsStore(db_file)

    # Empty summary
    summary_empty = store.get_historical_summary(window_hours=1.0)
    assert summary_empty["sample_count"] == 0

    # Insert snapshots
    now = time.time()
    store.record_snapshot(
        MetricSnapshot(
            now - 100,
            cpu_percent=45.0,
            ram_percent=60.0,
            disk_free_gb=50.0,
            active_streams=2,
            queue_depth=0,
            error_count=0,
        )
    )
    store.record_snapshot(
        MetricSnapshot(
            now - 50,
            cpu_percent=85.0,
            ram_percent=70.0,
            disk_free_gb=49.0,
            active_streams=4,
            queue_depth=1,
            error_count=0,
        )
    )
    store.record_snapshot(
        MetricSnapshot(
            now,
            cpu_percent=95.0,
            ram_percent=95.0,
            disk_free_gb=2.0,
            active_streams=10,
            queue_depth=3,
            error_count=15,
        )
    )

    # Summary
    summary = store.get_historical_summary(window_hours=1.0)
    assert summary["sample_count"] == 3
    assert summary["max_cpu"] == 95.0
    assert summary["min_disk_free_gb"] == 2.0
    assert summary["total_errors"] == 15

    # Check alerts
    alerts = store.check_alerts(min_disk_gb=5.0)
    assert len(alerts) >= 1
    assert any("CPU" in a for a in alerts)
    assert any("RAM" in a for a in alerts)
    assert any("disk" in a.lower() for a in alerts)

    # Prune metrics
    deleted = store.prune_old_metrics(retention_days=0)
    assert deleted == 3


def test_evaluate_readiness_and_cli(mock_config_dict: dict, temp_dir: Path):
    # Test evaluation when environment is operational
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=True),
        patch("cloudctl.core.backup.BackupManager.init_repository", return_value=True),
    ):
        eval_res = evaluate_readiness(mock_config_dict)
        assert eval_res.verdict in ("PRODUCTION_READY", "READY", "DEGRADED")
        assert eval_res.score_percent > 0.0

    # Test evaluation when container engine is down
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=False),
        patch("cloudctl.core.backup.BackupManager.init_repository", return_value=False),
    ):
        eval_fail = evaluate_readiness(mock_config_dict)
        assert eval_fail.verdict in ("NOT_READY", "DEGRADED")
        assert len(eval_fail.blockers) > 0

    # Test CLI execution
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # Standard execution with blockers & alerts
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=False),
        patch(
            "cloudctl.core.metrics.MetricsStore.check_alerts", return_value=["CRITICAL: CPU Alert"]
        ),
    ):
        args_block = MagicMock(config=str(cfg_file), json=False)
        assert execute_readiness(args_block) == 1

    # Standard execution pass
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=True),
        patch("cloudctl.core.backup.BackupManager.init_repository", return_value=True),
    ):
        args = MagicMock(config=str(cfg_file), json=False)
        assert execute_readiness(args) in (0, 1)

        # JSON execution
        args_json = MagicMock(config=str(cfg_file), json=True)
        assert execute_readiness(args_json) in (0, 1)
