"""Unit tests for performance metrics, resource profiles, and benchmark runner."""

from pathlib import Path

from cloudctl.core.performance import (
    PROFILES,
    collect_live_metrics,
    detect_resource_profile,
    run_benchmark,
)


def test_resource_profile_detection():
    prof_auto = detect_resource_profile()
    assert prof_auto.name in PROFILES
    assert prof_auto.max_concurrent_streams >= 2

    prof_tiny = detect_resource_profile("TINY")
    assert prof_tiny.name == "TINY"
    assert prof_tiny.max_transcode_jobs == 0

    prof_media = detect_resource_profile("MEDIA")
    assert prof_media.name == "MEDIA"
    assert prof_media.max_concurrent_streams == 100


def test_live_metrics_collection(temp_dir: Path):
    metrics = collect_live_metrics(temp_dir, active_streams=2, queue_depth=1)
    assert metrics.cpu_percent >= 0.0
    assert metrics.ram_percent > 0.0
    assert metrics.disk_free_gb > 0.0
    assert metrics.status in ("PASS", "WARN", "CRITICAL")


def test_benchmark_runner(temp_dir: Path):
    bench_dir = temp_dir / "bench_target"
    report = run_benchmark(bench_dir, profile_override="SMALL")

    assert report.profile_name == "SMALL"
    assert report.disk_write_mbs > 0
    assert report.disk_read_mbs > 0
    assert report.cpu_score_mops > 0
    assert report.recommended_concurrency == 5
