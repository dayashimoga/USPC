"""Doctor diagnostic checks and remediation command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.container import ContainerManager
from cloudctl.core.health import HealthChecker
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.doctor")


def execute_doctor(args: argparse.Namespace) -> int:
    """Run comprehensive system diagnostic checks."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    checker = HealthChecker(config)
    report = checker.run_all_checks()

    print("\n" + "=" * 70)
    print(" USPC Diagnostic Doctor")
    print("=" * 70)

    issues_found = 0
    for check in report.checks:
        if check.status != "HEALTHY":
            issues_found += 1
            print(f" [!] {check.component} - {check.name}: {check.message}")
            if check.remediation:
                print(f"     Recommended fix: {check.remediation}")
                if getattr(args, "fix", False):
                    logger.info(f"Attempting automatic remediation for '{check.name}'...")
                    # Auto-restart stopped containers
                    if "Container:" in check.name:
                        c_name = check.name.split("Container: ")[-1].strip()
                        cm = ContainerManager(config["runtime"]["engine"])
                        cm.start_container(c_name)
                        print(f"     -> Started container {c_name}")

    if issues_found == 0:
        print(" All diagnostic checks passed! System is operating normally.")
        print("=" * 70 + "\n")
        return 0
    else:
        print(f"\n Found {issues_found} issue(s). Address remediations above.")
        print("=" * 70 + "\n")
        return 1
