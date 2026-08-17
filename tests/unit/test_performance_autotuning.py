"""Unit tests for performance auto-tuning, budget gates, and retention policies."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cloudctl.core.metrics import get_retention_policy_days
from cloudctl.core.performance import auto_tune_from_hardware, validate_performance_budgets


def test_auto_tune_from_hardware_profiles():
    # 1. Tiny profile (< 2GB RAM or 1 CPU)
    mock_host_tiny = MagicMock()
    mock_host_tiny.total_ram_gb = 1.5
    mock_host_tiny.cpu_cores = 1

    with patch("cloudctl.core.performance.detect_host", return_value=mock_host_tiny):
        tuned = auto_tune_from_hardware()
        assert tuned["profile"] == "tiny"
        assert tuned["max_concurrent_streams"] == 2
        assert tuned["max_transcode_concurrency"] == 0

    # 2. Standard profile (4 - 8GB RAM, 4 Cores)
    mock_host_std = MagicMock()
    mock_host_std.total_ram_gb = 6.0
    mock_host_std.cpu_cores = 4

    with patch("cloudctl.core.performance.detect_host", return_value=mock_host_std):
        tuned_std = auto_tune_from_hardware()
        assert tuned_std["profile"] == "standard"
        assert tuned_std["max_concurrent_streams"] == 15
        assert tuned_std["db_connection_pool_size"] == 25

    # 3. Media profile (>= 16GB RAM)
    mock_host_media = MagicMock()
    mock_host_media.total_ram_gb = 32.0
    mock_host_media.cpu_cores = 16

    with patch("cloudctl.core.performance.detect_host", return_value=mock_host_media):
        tuned_media = auto_tune_from_hardware()
        assert tuned_media["profile"] == "media"
        assert tuned_media["max_concurrent_streams"] == 100

    # 4. Preserve user override
    base_cfg = {"performance": {"max_concurrent_streams": 99}}
    with patch("cloudctl.core.performance.detect_host", return_value=mock_host_std):
        tuned_override = auto_tune_from_hardware(base_config=base_cfg)
        assert tuned_override["max_concurrent_streams"] == 99


def test_validate_performance_budgets_pass_and_fail():
    config = {
        "performance": {
            "budgets": {
                "max_listing_p95_ms": 50.0,
                "max_stream_start_p95_ms": 100.0,
                "max_api_p99_ms": 200.0,
                "max_startup_seconds": 30.0,
                "min_upload_throughput_mb_s": 10.0,
            }
        }
    }

    # Pass measurements
    passing_measurements = {
        "listing_p95_ms": 32.5,
        "stream_start_p95_ms": 68.0,
        "api_p99_ms": 120.0,
        "startup_seconds": 8.4,
        "upload_throughput_mb_s": 24.5,
    }
    res_pass = validate_performance_budgets(config, passing_measurements)
    assert res_pass["passed"] is True
    assert len(res_pass["violations"]) == 0
    assert res_pass["checks"]["max_listing_p95_ms"]["passed"] is True

    # Failing measurements
    failing_measurements = {
        "listing_p95_ms": 85.0,  # exceeds 50.0
        "stream_start_p95_ms": 150.0,  # exceeds 100.0
        "api_p99_ms": 250.0,  # exceeds 200.0
        "startup_seconds": 45.0,  # exceeds 30.0
        "upload_throughput_mb_s": 4.2,  # below 10.0
    }
    res_fail = validate_performance_budgets(config, failing_measurements)
    assert res_fail["passed"] is False
    assert len(res_fail["violations"]) == 5


def test_retention_policy_mapping():
    assert get_retention_policy_days("minimal") == 7
    assert get_retention_policy_days("standard") == 30
    assert get_retention_policy_days("full") == 90
    assert get_retention_policy_days("cluster") == 180
    assert get_retention_policy_days("unknown") == 30
