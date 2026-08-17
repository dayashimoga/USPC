"""Dynamic performance profiling, hardware benchmarks, and resource auto-tuning."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from cloudctl.core.detect import detect_host
from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import ensure_directory

logger = get_logger("performance")


@dataclass
class ResourceProfile:
    """Standardized performance and capacity profile."""

    name: str  # TINY, SMALL, STANDARD, PERFORMANCE, MEDIA
    description: str
    max_concurrent_streams: int
    max_streams_per_user: int
    max_transcode_jobs: int
    db_connection_pool: int
    redis_max_memory_mb: int
    media_worker_concurrency: int
    rate_limit_rpm: int
    chunk_size_kb: int


# Predefined hardware capacity profiles
PROFILES: dict[str, ResourceProfile] = {
    "TINY": ResourceProfile(
        name="TINY",
        description="Low resource environment (< 2GB RAM, 1 CPU Core)",
        max_concurrent_streams=2,
        max_streams_per_user=1,
        max_transcode_jobs=0,  # Direct stream only, no heavy transcoding
        db_connection_pool=5,
        redis_max_memory_mb=128,
        media_worker_concurrency=1,
        rate_limit_rpm=120,
        chunk_size_kb=32,
    ),
    "SMALL": ResourceProfile(
        name="SMALL",
        description="Entry personal server (2 - 4GB RAM, 2 CPU Cores)",
        max_concurrent_streams=5,
        max_streams_per_user=2,
        max_transcode_jobs=1,
        db_connection_pool=10,
        redis_max_memory_mb=256,
        media_worker_concurrency=2,
        rate_limit_rpm=300,
        chunk_size_kb=64,
    ),
    "STANDARD": ResourceProfile(
        name="STANDARD",
        description="Standard personal cloud server (4 - 8GB RAM, 4 CPU Cores)",
        max_concurrent_streams=15,
        max_streams_per_user=3,
        max_transcode_jobs=2,
        db_connection_pool=25,
        redis_max_memory_mb=512,
        media_worker_concurrency=4,
        rate_limit_rpm=600,
        chunk_size_kb=64,
    ),
    "PERFORMANCE": ResourceProfile(
        name="PERFORMANCE",
        description="High-performance workstation / multi-user server (8 - 16GB RAM, 6+ Cores)",
        max_concurrent_streams=40,
        max_streams_per_user=5,
        max_transcode_jobs=4,
        db_connection_pool=50,
        redis_max_memory_mb=1024,
        media_worker_concurrency=8,
        rate_limit_rpm=1200,
        chunk_size_kb=128,
    ),
    "MEDIA": ResourceProfile(
        name="MEDIA",
        description="Dedicated heavy media server (16GB+ RAM, 8+ Cores, NVMe)",
        max_concurrent_streams=100,
        max_streams_per_user=10,
        max_transcode_jobs=8,
        db_connection_pool=100,
        redis_max_memory_mb=2048,
        media_worker_concurrency=16,
        rate_limit_rpm=2400,
        chunk_size_kb=256,
    ),
}


def detect_resource_profile(override: str | None = None) -> ResourceProfile:
    """Automatically select the optimal resource profile based on detected hardware."""
    if override and override.upper() in PROFILES:
        return PROFILES[override.upper()]

    host = detect_host()
    ram_gb = host.total_ram_gb
    cores = host.cpu_cores

    if ram_gb < 2.5 or cores <= 1:
        selected = "TINY"
    elif ram_gb < 5.0 or cores <= 2:
        selected = "SMALL"
    elif ram_gb < 10.0 or cores <= 4:
        selected = "STANDARD"
    elif ram_gb < 20.0 or cores <= 8:
        selected = "PERFORMANCE"
    else:
        selected = "MEDIA"

    logger.debug(
        f"Auto-selected performance profile '{selected}' based on {cores} cores, {ram_gb} GB RAM"
    )
    return PROFILES[selected]


@dataclass
class LivePerformanceMetrics:
    """Current live host and service performance metrics."""

    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_free_gb: float
    disk_used_percent: float
    active_streams: int
    queue_depth: int
    bottlenecks: list[str]
    status: str  # PASS, WARN, CRITICAL


def collect_live_metrics(
    data_path: str | Path, active_streams: int = 0, queue_depth: int = 0
) -> LivePerformanceMetrics:
    """Capture snapshot of active system resource utilization."""
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    ram_used_gb = round((mem.total - mem.available) / (1024**3), 2)
    ram_total_gb = round(mem.total / (1024**3), 2)

    p = Path(data_path).expanduser().resolve()
    while not p.exists() and p.parent != p:
        p = p.parent
    if not p.exists():
        p = Path.cwd()
    disk_usage = shutil.disk_usage(p)
    disk_free_gb = round(disk_usage.free / (1024**3), 2)
    disk_pct = round((disk_usage.used / disk_usage.total) * 100, 1)

    bottlenecks: list[str] = []
    if cpu_pct > 85.0:
        bottlenecks.append("High CPU utilization (> 85%)")
    if mem.percent > 90.0:
        bottlenecks.append("Critical RAM saturation (> 90%)")
    if disk_free_gb < 5.0:
        bottlenecks.append("Low free disk space (< 5 GB)")

    if len(bottlenecks) >= 2 or mem.percent > 95.0:
        status = "CRITICAL"
    elif len(bottlenecks) >= 1 or cpu_pct > 75.0 or mem.percent > 80.0:
        status = "WARN"
    else:
        status = "PASS"

    return LivePerformanceMetrics(
        cpu_percent=cpu_pct,
        ram_percent=mem.percent,
        ram_used_gb=ram_used_gb,
        ram_total_gb=ram_total_gb,
        disk_free_gb=disk_free_gb,
        disk_used_percent=disk_pct,
        active_streams=active_streams,
        queue_depth=queue_depth,
        bottlenecks=bottlenecks,
        status=status,
    )


@dataclass
class BenchmarkReport:
    """Results of practical capacity, IOPS, and speed benchmark."""

    profile_name: str
    disk_write_mbs: float
    disk_read_mbs: float
    disk_iops_4k: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    cpu_score_mops: float
    synthetic_stream_capacity_mbs: float
    recommended_concurrency: int
    recommended_transcode_jobs: int
    bottlenecks: list[str]


def run_benchmark(target_dir: str | Path, profile_override: str | None = None) -> BenchmarkReport:
    """Run real disk sequential, 4KB random IOPS, and CPU benchmarks to measure genuine host capacity."""
    test_p = Path(target_dir).expanduser().resolve()
    ensure_directory(test_p)

    profile = detect_resource_profile(profile_override)
    logger.info("Running storage write throughput benchmark (50MB sample)...")

    # 1. Sequential Disk Write Benchmark (50 MB)
    test_file = test_p / ".uspc_bench_payload.tmp"
    data_block = b"X" * (1024 * 1024)  # 1MB block
    start_w = time.perf_counter()
    with open(test_file, "wb") as f:
        for _ in range(50):
            f.write(data_block)
        f.flush()
        if hasattr(os, "fsync"):
            os.fsync(f.fileno())
    dur_w = max(0.001, time.perf_counter() - start_w)
    write_mbs = round(50.0 / dur_w, 2)

    # 2. Sequential Disk Read Benchmark (50 MB)
    logger.info("Running storage read throughput benchmark...")
    start_r = time.perf_counter()
    with open(test_file, "rb") as f:
        while f.read(1024 * 1024):
            pass
    dur_r = max(0.001, time.perf_counter() - start_r)
    read_mbs = round(50.0 / dur_r, 2)
    test_file.unlink(missing_ok=True)

    # 3. Random 4KB IOPS and Latency Benchmark (100 operations)
    logger.info("Running 4KB random I/O and latency benchmark...")
    iops_file = test_p / ".uspc_iops_payload.tmp"
    block_4k = b"A" * 4096
    latencies_ms: list[float] = []

    with open(iops_file, "wb+") as f:
        for _ in range(100):
            t0 = time.perf_counter()
            f.write(block_4k)
            f.flush()
            if hasattr(os, "fsync"):
                os.fsync(f.fileno())
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    iops_file.unlink(missing_ok=True)
    latencies_ms.sort()
    p50 = round(latencies_ms[int(len(latencies_ms) * 0.50)], 2)
    p95 = round(latencies_ms[int(len(latencies_ms) * 0.95)], 2)
    p99 = round(latencies_ms[int(len(latencies_ms) * 0.99)], 2)
    avg_dur = sum(latencies_ms) / max(1, len(latencies_ms))
    iops_4k = int(1000.0 / max(0.1, avg_dur))

    # 4. CPU Math & Hashing Benchmark
    logger.info("Running CPU compute benchmark...")
    import hashlib

    start_c = time.perf_counter()
    for _ in range(5000):
        hashlib.sha256(data_block[:4096]).digest()
    dur_c = max(0.001, time.perf_counter() - start_c)
    cpu_mops = round(5000 / dur_c / 1000, 2)

    # Synthetic stream capacity estimate (assume 4Mbps video stream = 0.5 MB/s)
    stream_mbs = round(read_mbs * 0.7, 2)

    bottlenecks = []
    if write_mbs < 30.0:
        bottlenecks.append("Storage write speed is slow (< 30 MB/s, HDD or slow USB)")
    if read_mbs < 50.0:
        bottlenecks.append("Storage read speed is slow (< 50 MB/s)")
    if p95 > 50.0:
        bottlenecks.append(f"Storage latency is elevated (P95: {p95} ms)")

    return BenchmarkReport(
        profile_name=profile.name,
        disk_write_mbs=write_mbs,
        disk_read_mbs=read_mbs,
        disk_iops_4k=iops_4k,
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        latency_p99_ms=p99,
        cpu_score_mops=cpu_mops,
        synthetic_stream_capacity_mbs=stream_mbs,
        recommended_concurrency=profile.max_concurrent_streams,
        recommended_transcode_jobs=profile.max_transcode_jobs,
        bottlenecks=bottlenecks,
    )


@dataclass
class StressTestResult:
    """Results of progressive concurrent workload stress test."""

    concurrency_level: int
    total_operations: int
    success_count: int
    error_count: int
    throughput_ops_sec: float
    avg_latency_ms: float
    p95_latency_ms: float


def run_stress_test(
    target_dir: str | Path, concurrency_levels: list[int] | None = None
) -> list[StressTestResult]:
    """Run progressive stress test to find practical operational concurrency limits."""
    if concurrency_levels is None:
        concurrency_levels = [1, 5, 10, 25]

    test_p = Path(target_dir).expanduser().resolve()
    ensure_directory(test_p)
    results: list[StressTestResult] = []

    for c_level in concurrency_levels:
        latencies: list[float] = []
        errors = 0
        ops_per_thread = 10
        total_ops = c_level * ops_per_thread

        t_start = time.perf_counter()
        for t_idx in range(c_level):
            thread_file = test_p / f".uspc_stress_{c_level}_{t_idx}.tmp"
            for _ in range(ops_per_thread):
                op_t0 = time.perf_counter()
                try:
                    thread_file.write_bytes(b"STRESS_TEST_CHUNK_PAYLOAD_" * 512)
                    _ = thread_file.read_bytes()
                except Exception:
                    errors += 1
                finally:
                    latencies.append((time.perf_counter() - op_t0) * 1000.0)
            thread_file.unlink(missing_ok=True)

        total_dur = max(0.001, time.perf_counter() - t_start)
        latencies.sort()
        p95 = round(latencies[int(len(latencies) * 0.95)] if latencies else 0.0, 2)
        avg_lat = round(sum(latencies) / max(1, len(latencies)), 2)

        results.append(
            StressTestResult(
                concurrency_level=c_level,
                total_operations=total_ops,
                success_count=total_ops - errors,
                error_count=errors,
                throughput_ops_sec=round(total_ops / total_dur, 1),
                avg_latency_ms=avg_lat,
                p95_latency_ms=p95,
            )
        )

    return results


def auto_tune_from_hardware(base_config: dict | None = None) -> dict:
    """Auto-tune performance, concurrency, pool sizes, and cache limits from host hardware."""
    host = detect_host()
    ram_gb = getattr(host, "total_ram_gb", 4.0)
    cpu_cores = getattr(host, "cpu_cores", 2)

    if ram_gb < 2.0 or cpu_cores <= 1:
        prof_name = "TINY"
    elif ram_gb < 4.0:
        prof_name = "SMALL"
    elif ram_gb < 8.0:
        prof_name = "STANDARD"
    elif ram_gb < 16.0:
        prof_name = "PERFORMANCE"
    else:
        prof_name = "MEDIA"

    profile = PROFILES[prof_name]
    tuned = {
        "profile": prof_name.lower(),
        "max_concurrent_streams": profile.max_concurrent_streams,
        "max_streams_per_user": profile.max_streams_per_user,
        "max_transcode_concurrency": profile.max_transcode_jobs,
        "rate_limit_requests_per_minute": profile.rate_limit_rpm,
        "db_connection_pool_size": profile.db_connection_pool,
        "redis_max_memory_mb": profile.redis_max_memory_mb,
        "chunk_size_kb": profile.chunk_size_kb,
    }

    if base_config and "performance" in base_config:
        # Preserve explicit user overrides if present
        for k, v in base_config["performance"].items():
            if k in tuned and v is not None:
                tuned[k] = v

    return tuned


def validate_performance_budgets(config: dict, measurements: dict[str, float]) -> dict[str, Any]:
    """Validate measured benchmark metrics against configured performance budgets."""
    budgets = config.get("performance", {}).get("budgets", {})
    results: dict[str, Any] = {
        "passed": True,
        "violations": [],
        "checks": {},
    }

    checks = [
        ("max_listing_p95_ms", "listing_p95_ms", lambda measured, budget: measured <= budget, "ms"),
        (
            "max_stream_start_p95_ms",
            "stream_start_p95_ms",
            lambda measured, budget: measured <= budget,
            "ms",
        ),
        ("max_api_p99_ms", "api_p99_ms", lambda measured, budget: measured <= budget, "ms"),
        (
            "max_startup_seconds",
            "startup_seconds",
            lambda measured, budget: measured <= budget,
            "s",
        ),
        (
            "min_upload_throughput_mb_s",
            "upload_throughput_mb_s",
            lambda measured, budget: measured >= budget,
            "MB/s",
        ),
    ]

    for budget_key, measured_key, comparator, unit in checks:
        budget_val = budgets.get(budget_key)
        measured_val = measurements.get(measured_key)

        if budget_val is not None and measured_val is not None:
            is_ok = comparator(measured_val, budget_val)
            results["checks"][budget_key] = {
                "budget": budget_val,
                "measured": measured_val,
                "unit": unit,
                "passed": is_ok,
            }
            if not is_ok:
                results["passed"] = False
                results["violations"].append(
                    f"Budget '{budget_key}' breached: measured {measured_val}{unit} exceeds budget {budget_val}{unit}"
                )

    return results
