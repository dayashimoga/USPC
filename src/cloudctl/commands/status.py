"""System status query and dashboard command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager
from cloudctl.core.health import HealthChecker
from cloudctl.core.reporting import print_status_dashboard


def execute_status(args: argparse.Namespace) -> int:
    """Execute status reporting."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    checker = HealthChecker(config)
    report = checker.run_all_checks()
    print_status_dashboard(report, config, json_output=getattr(args, "json", False))
    return 0 if report.overall_status == "HEALTHY" else 1
