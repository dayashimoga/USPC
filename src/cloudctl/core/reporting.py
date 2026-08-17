"""Formatted console dashboards and structured reporting."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from cloudctl.core.health import SystemHealthReport
from cloudctl.core.security import SecurityCheckResult


def print_status_dashboard(
    report: SystemHealthReport, config: dict[str, Any], json_output: bool = False
) -> None:
    """Render the system status dashboard."""
    if json_output:
        payload = {
            "overall_status": report.overall_status,
            "cloud_name": config.get("cloud", {}).get("name", "unknown"),
            "domain": config.get("cloud", {}).get("domain", "unknown"),
            "checks": [asdict(c) for c in report.checks],
            "containers": [asdict(c) for c in report.containers],
        }
        print(json.dumps(payload, indent=2))
        return

    cloud_name = config.get("cloud", {}).get("name", "mycloud")
    domain = config.get("cloud", {}).get("domain", "mycloud.local")

    print("\n" + "=" * 70)
    print(f" USPC Health Dashboard - [{cloud_name.upper()}] ({domain})")
    print("=" * 70)

    # Status banner
    badge = {
        "HEALTHY": "[ OK / HEALTHY ]",
        "DEGRADED": "[ WARN / DEGRADED ]",
        "UNHEALTHY": "[ CRITICAL / UNHEALTHY ]",
    }.get(report.overall_status, "[ UNKNOWN ]")

    print(f" Overall Status: {badge}\n")

    print(" COMPONENT CHECKS:")
    print(" -----------------")
    for check in report.checks:
        icon = {
            "HEALTHY": "[+]",
            "DEGRADED": "[!]",
            "UNHEALTHY": "[X]",
        }.get(check.status, "[?]")
        print(f"  {icon} {check.component:<10} | {check.name:<25} : {check.message}")
        if check.remediation:
            print(f"      -> Remediation: {check.remediation}")

    print("\n CONTAINERS:")
    print(" -----------")
    for c in report.containers:
        print(
            f"  * {c.name:<18} | Status: {c.status:<10} | ID: {c.id or 'N/A':<12} | Image: {c.image or 'N/A'}"
        )

    print("=" * 70 + "\n")


def print_security_report(results: list[SecurityCheckResult], strict: bool = False) -> int:
    """Print formatted security audit results."""
    print("\n" + "=" * 70)
    print(" USPC Security Audit Report")
    print("=" * 70)

    has_fail = False
    has_warn = False

    for res in results:
        badge = {
            "PASS": "[PASS]",
            "WARN": "[WARN]",
            "FAIL": "[FAIL]",
        }.get(res.status, "[?]")

        if res.status == "FAIL":
            has_fail = True
        elif res.status == "WARN":
            has_warn = True

        print(f" {badge} {res.name}")
        print(f"        Details: {res.details}")
        if res.remediation:
            print(f"        Remediation: {res.remediation}")
        print()

    print("=" * 70)
    if has_fail or (strict and has_warn):
        print(" Security audit status: FAILED (Address required remediations above)")
        print("=" * 70 + "\n")
        return 1
    else:
        print(" Security audit status: PASSED")
        print("=" * 70 + "\n")
        return 0
