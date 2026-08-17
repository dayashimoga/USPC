"""Production readiness evaluation and compliance verification command."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from cloudctl.core.backup import BackupManager
from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import detect_host
from cloudctl.core.health import HealthChecker
from cloudctl.core.logging import get_logger
from cloudctl.core.metrics import MetricsStore
from cloudctl.core.performance import collect_live_metrics, detect_resource_profile
from cloudctl.core.security import SecurityChecker
from cloudctl.utils.validators import is_valid_port

logger = get_logger("cmd.readiness")


@dataclass
class ReadinessEvaluation:
    """Aggregated production readiness verdict."""

    verdict: str  # PRODUCTION_READY, READY, DEGRADED, NOT_READY
    score_percent: float
    host_summary: dict[str, Any]
    capacity: dict[str, Any]
    health: dict[str, Any]
    security: dict[str, Any]
    backup: dict[str, Any]
    observability: dict[str, Any]
    layers: dict[str, str]  # infrastructure, application, security, recovery, external
    active_alerts: list[str]
    blockers: list[str]


def evaluate_readiness(
    config: dict[str, Any], config_path: str | None = None
) -> ReadinessEvaluation:
    """Conduct exhaustive system audit across 5 layers and generate readiness evaluation."""
    blockers: list[str] = []
    total_checks = 0
    passed_checks = 0

    # Layer 1: Infrastructure & Host Discovery
    host = detect_host()
    host_summary = {
        "os": f"{host.os_name} {host.os_release} ({host.arch})",
        "cores": host.cpu_cores,
        "ram_gb": host.total_ram_gb,
        "container_engine": f"{host.container_engine} {host.engine_version}",
        "is_admin": host.is_root_or_admin,
    }

    cm = ContainerManager(engine=config.get("runtime", {}).get("engine", "auto"))
    total_checks += 1
    if cm.is_available():
        passed_checks += 1
        layer_infra = "PASS"
    else:
        blockers.append(f"Container engine '{cm.engine}' is not running or unavailable.")
        layer_infra = "FAIL"

    # Layer 2: Application & Container Services Health
    hc = HealthChecker(config)
    health_rep = hc.run_all_checks()
    layer_app = "PASS"
    for c in health_rep.checks:
        total_checks += 1
        if c.status == "HEALTHY":
            passed_checks += 1
        elif c.status == "UNHEALTHY":
            blockers.append(f"Service Check Failed: {c.component} - {c.name}: {c.message}")
            layer_app = "FAIL"
        elif c.status == "DEGRADED" and layer_app != "FAIL":
            layer_app = "WARN"

    # Layer 3: Security & Authorization Audit
    cm_mgr = ConfigManager(config_path=config_path)
    sc = SecurityChecker(config, cm_mgr.repo_root)
    sec_results = sc.run_all_checks()
    layer_sec = "PASS"
    for s in sec_results:
        total_checks += 1
        if s.status == "PASS":
            passed_checks += 1
        elif s.status == "FAIL":
            blockers.append(f"Security Blocker: {s.name} - {s.details}")
            layer_sec = "FAIL"
        elif s.status == "WARN" and layer_sec != "FAIL":
            layer_sec = "WARN"

    # Layer 4: Backup, Storage & Disaster Recovery
    bm = BackupManager(config)
    repo_ok = bm.init_repository()
    total_checks += 1
    if repo_ok:
        passed_checks += 1
        layer_rec = "PASS"
    else:
        blockers.append("Backup repository is uninitialized or inaccessible.")
        layer_rec = "FAIL"

    # Layer 5: Observability & Capacity Management
    profile = detect_resource_profile(config.get("performance", {}).get("profile"))
    live = collect_live_metrics(config.get("storage", {}).get("data_path", "~/.uspc/data"))
    ms = MetricsStore()
    ms.enforce_storage_limit(max_size_bytes=100 * 1024 * 1024)
    alerts = ms.check_alerts()

    layer_obs = "PASS"
    if live.status == "CRITICAL" or len(alerts) > 0:
        layer_obs = "WARN" if len(alerts) <= 2 else "FAIL"

    # Layer 6: External Remote Access & Network Isolation
    net_mode = config.get("network", {}).get("mode", "private")
    headscale_port = config.get("network", {}).get("headscale_port", 8080)
    layer_remote = "PASS"
    total_checks += 1
    if net_mode == "private":
        if is_valid_port(headscale_port):
            passed_checks += 1
            layer_remote = "PASS"
        else:
            blockers.append(f"Invalid Headscale VPN control port: {headscale_port}")
            layer_remote = "FAIL"
    elif net_mode == "public":
        if not config.get("security", {}).get("tls_enabled", False):
            blockers.append("Public access mode enabled without TLS encryption.")
            layer_remote = "FAIL"
        else:
            passed_checks += 1
            layer_remote = "WARN"

    layers = {
        "infrastructure": layer_infra,
        "application": layer_app,
        "security": layer_sec,
        "recovery": layer_rec,
        "observability": layer_obs,
        "external_remote": layer_remote,
    }

    capacity = {
        "profile_name": profile.name,
        "configured_max_streams": config.get("performance", {}).get(
            "max_concurrent_streams", profile.max_concurrent_streams
        ),
        "profile_concurrency_limit": profile.max_concurrent_streams,
        "current_active_streams": live.active_streams,
        "current_cpu_percent": live.cpu_percent,
        "current_ram_percent": live.ram_percent,
        "current_disk_free_gb": live.disk_free_gb,
    }

    # Calculate overall readiness verdict
    score = round((passed_checks / max(1, total_checks)) * 100, 1)

    if not cm.is_available() or len(blockers) >= 3 or any(v == "FAIL" for v in layers.values()):
        verdict = "NOT_READY" if not cm.is_available() or len(blockers) >= 2 else "DEGRADED"
    elif len(blockers) > 0 or len(alerts) > 0 or live.status == "CRITICAL":
        verdict = "DEGRADED"
    elif any(v == "WARN" for v in layers.values()):
        verdict = "READY"
    else:
        verdict = "PRODUCTION_READY"

    return ReadinessEvaluation(
        verdict=verdict,
        score_percent=score,
        host_summary=host_summary,
        capacity=capacity,
        health={
            "overall_status": health_rep.overall_status,
            "checks_count": len(health_rep.checks),
        },
        security={
            "passed": sum(1 for s in sec_results if s.status == "PASS"),
            "total": len(sec_results),
        },
        backup={"initialized": repo_ok, "target": str(bm.target_path)},
        observability={
            "metrics_db_bytes": ms.get_db_size_bytes(),
            "alert_count": len(alerts),
        },
        layers=layers,
        active_alerts=alerts,
        blockers=blockers,
    )


def execute_readiness(args: argparse.Namespace) -> int:
    """Execute readiness evaluation and print structured report."""
    cfg_mgr = ConfigManager(config_path=getattr(args, "config", None))
    config = cfg_mgr.load_config()
    eval_res = evaluate_readiness(config, config_path=getattr(args, "config", None))

    if getattr(args, "json", False):
        print(json.dumps(asdict(eval_res), indent=2))
        return 0 if eval_res.verdict in ("READY", "PRODUCTION_READY") else 1

    print("\n" + "=" * 78)
    print(" USPC Production Readiness Assessment Report")
    print("=" * 78)

    verdict_colors = {
        "PRODUCTION_READY": "[PASS] PRODUCTION READY",
        "READY": "[OK] READY (Minor Warnings)",
        "DEGRADED": "[WARN] DEGRADED (Requires Attention)",
        "NOT_READY": "[FAIL] NOT READY",
    }
    print(f" Status Verdict : {verdict_colors.get(eval_res.verdict, eval_res.verdict)}")
    print(f" Readiness Score: {eval_res.score_percent}%")
    print(
        f" Host Platform  : {eval_res.host_summary['os']} | Cores: {eval_res.host_summary['cores']} | RAM: {eval_res.host_summary['ram_gb']} GB"
    )
    print(f" Container Engine: {eval_res.host_summary['container_engine']}")
    print("-" * 78)

    print(" 6-LAYER READINESS AUDIT:")
    for lname, lstatus in eval_res.layers.items():
        print(f"  - {lname.replace('_', ' ').title():<26}: [{lstatus}]")
    print("-" * 78)

    print(" CAPACITY & RESOURCE PROFILE:")
    print(f"  - Resource Profile   : {eval_res.capacity['profile_name']}")
    print(
        f"  - Configured Streams : {eval_res.capacity['configured_max_streams']} (Profile Max: {eval_res.capacity['profile_concurrency_limit']})"
    )
    print(
        f"  - Current Load       : CPU {eval_res.capacity['current_cpu_percent']}%, RAM {eval_res.capacity['current_ram_percent']}%, Disk Free: {eval_res.capacity['current_disk_free_gb']} GB"
    )
    print("-" * 78)

    print(" SUBSYSTEM INTEGRITY:")
    print(
        f"  - Services & Health  : {eval_res.health['overall_status']} ({eval_res.health['checks_count']} checks verified)"
    )
    print(
        f"  - Security Audits    : {eval_res.security['passed']}/{eval_res.security['total']} checks passed"
    )
    print(
        f"  - Backup Repository  : {'ONLINE' if eval_res.backup['initialized'] else 'OFFLINE'} ({eval_res.backup['target']})"
    )
    print("-" * 78)

    if eval_res.blockers:
        print(" BLOCKERS / ACTION ITEMS:")
        for b in eval_res.blockers:
            print(f"  [!] {b}")
        print("-" * 78)

    if eval_res.active_alerts:
        print(" ACTIVE ALERTS:")
        for a in eval_res.active_alerts:
            print(f"  [*] {a}")
        print("-" * 78)

    print("=" * 78 + "\n")
    return 0 if eval_res.verdict in ("READY", "PRODUCTION_READY") else 1
