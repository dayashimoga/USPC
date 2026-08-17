"""Hardware benchmark and capacity measurement command."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from cloudctl.core.config import ConfigManager
from cloudctl.core.performance import run_benchmark, run_stress_test


def execute_benchmark(args: argparse.Namespace) -> int:
    """Run genuine disk, compute, IOPS, and progressive stress benchmarks."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()

    target_dir = config.get("storage", {}).get("data_path", "~/.uspc/data")
    profile_override = getattr(args, "profile", None)
    stress_mode = getattr(args, "stress", False)

    print("\n" + "=" * 75)
    print(" USPC Hardware, IOPS & Throughput Benchmark")
    print("=" * 75)
    print(" Running active throughput and latency measurements, please wait...")

    report = run_benchmark(target_dir, profile_override)
    stress_results = run_stress_test(target_dir) if stress_mode else []

    if getattr(args, "json", False):
        output = {"benchmark": asdict(report)}
        if stress_results:
            output["stress_test"] = [asdict(s) for s in stress_results]
        print(json.dumps(output, indent=2))
        return 0

    print(f"\n [BENCHMARK RESULTS - Profile: {report.profile_name}]")
    print(f"  * Sequential Disk Write  : {report.disk_write_mbs} MB/s")
    print(f"  * Sequential Disk Read   : {report.disk_read_mbs} MB/s")
    print(f"  * 4KB Random Write IOPS  : {report.disk_iops_4k} IOPS")
    print(
        f"  * I/O Latency (P50/P95)  : {report.latency_p50_ms} ms / {report.latency_p95_ms} ms (P99: {report.latency_p99_ms} ms)"
    )
    print(f"  * Compute Hash Score     : {report.cpu_score_mops} M-Ops/s")
    print(f"  * Max Stream Throughput  : ~{report.synthetic_stream_capacity_mbs} MB/s")
    print(f"  * Recommended Streams    : {report.recommended_concurrency} concurrent streams")
    print(f"  * Recommended Transcodes : {report.recommended_transcode_jobs} parallel jobs")

    if stress_results:
        print("\n [PROGRESSIVE CONCURRENCY STRESS TEST RESULTS]")
        print(
            f"  {'CONCURRENCY':<14} {'OPERATIONS':<12} {'SUCCESS':<10} {'THROUGHPUT':<18} {'P95 LATENCY':<12}"
        )
        print("  " + "-" * 66)
        for s in stress_results:
            print(
                f"  {s.concurrency_level:<14} {s.total_operations:<12} {s.success_count:<10} {f'{s.throughput_ops_sec} ops/s':<18} {f'{s.p95_latency_ms} ms':<12}"
            )

    if report.bottlenecks:
        print("\n [WARNINGS / BOTTLENECKS]")
        for b in report.bottlenecks:
            print(f"  [!] {b}")
    else:
        print("\n [STATUS: PASS] Storage and compute exceed baseline requirements.")

    print("=" * 75 + "\n")
    return 0
