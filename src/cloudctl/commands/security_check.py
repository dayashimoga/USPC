"""Security check command."""

from __future__ import annotations

import argparse

from cloudctl.core.config import ConfigManager, get_repo_root
from cloudctl.core.reporting import print_security_report
from cloudctl.core.security import SecurityChecker


def execute_security_check(args: argparse.Namespace) -> int:
    """Execute complete security audit."""
    cfg_mgr = ConfigManager(getattr(args, "config", None))
    config = cfg_mgr.load_config()
    checker = SecurityChecker(config, get_repo_root())
    results = checker.run_all_checks()
    return print_security_report(results, strict=getattr(args, "strict", False))
