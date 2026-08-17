"""Comprehensive tests for IOPS benchmarking, latency metrics, and progressive stress testing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from cloudctl.commands.benchmark import execute_benchmark
from cloudctl.core.performance import run_benchmark, run_stress_test


def test_run_benchmark_with_iops_and_latencies(temp_dir: Path):
    report = run_benchmark(temp_dir)
    assert report.profile_name in ("TINY", "SMALL", "STANDARD", "PERFORMANCE", "MEDIA")
    assert report.disk_write_mbs > 0.0
    assert report.disk_read_mbs > 0.0
    assert report.disk_iops_4k > 0
    assert report.latency_p50_ms >= 0.0
    assert report.latency_p95_ms >= 0.0
    assert report.cpu_score_mops > 0.0


def test_run_stress_test_levels(temp_dir: Path):
    results = run_stress_test(temp_dir, concurrency_levels=[1, 2])
    assert len(results) == 2
    for r in results:
        assert r.total_operations > 0
        assert r.success_count == r.total_operations
        assert r.error_count == 0
        assert r.throughput_ops_sec > 0.0
        assert r.avg_latency_ms >= 0.0


def test_execute_benchmark_cli_with_stress_and_json(temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_file.write_text(
        "version: '0.1.0'\nstorage:\n  data_path: '" + str(temp_dir).replace("\\", "/") + "'\n",
        encoding="utf-8",
    )

    # Regular benchmark
    args = MagicMock(config=str(cfg_file), profile=None, stress=False, json=False)
    assert execute_benchmark(args) == 0

    # With stress test
    args_stress = MagicMock(config=str(cfg_file), profile="tiny", stress=True, json=False)
    assert execute_benchmark(args_stress) == 0

    # With JSON output
    args_json = MagicMock(config=str(cfg_file), profile=None, stress=True, json=True)
    assert execute_benchmark(args_json) == 0
