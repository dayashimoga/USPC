"""Configuration management commands for USPC CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cloudctl.core.config import ConfigManager
from cloudctl.core.logging import get_logger

logger = get_logger("cmd.config")


def execute_config(args: argparse.Namespace) -> int:
    """Dispatch configuration subcommand."""
    action = getattr(args, "config_action", None)
    cm = ConfigManager(config_path=getattr(args, "config", None))

    if action == "validate":
        try:
            config = cm.load_config()
            print(f"Configuration is VALID (loaded from {cm.config_path}).")
            print(f"  - Cloud Domain: {config.get('cloud', {}).get('domain')}")
            print(f"  - Admin User  : {config.get('cloud', {}).get('admin_user')}")
            print(f"  - Network Mode: {config.get('network', {}).get('mode')}")
            print(
                f"  - Nextcloud   : port {config.get('services', {}).get('nextcloud', {}).get('port')}"
            )
            print(f"  - Media       : port {config.get('media', {}).get('port')}")
            return 0
        except Exception as e:
            sys.stderr.write(f"Configuration validation FAILED: {e}\n")
            return 1

    elif action == "diff":
        diffs = cm.diff_config()
        print(f"\nConfiguration Comparison & Provenance (Target: {cm.config_path})")
        print("=" * 80)
        print(f"{'SETTING':<36} {'CURRENT VALUE':<20} {'PROVENANCE':<15}")
        print("-" * 80)
        for d in diffs:
            cur_str = str(d["current"])
            if len(cur_str) > 18:
                cur_str = cur_str[:15] + "..."
            prov = d["provenance"]
            if prov == "USER-OVERRIDE":
                prov_label = "[USER-OVERRIDE]"
            elif prov == "AUTO":
                prov_label = "[AUTO]"
            else:
                prov_label = "DEFAULT"
            print(f"{d['key']:<36} {cur_str:<20} {prov_label:<15}")
        print("=" * 80 + "\n")
        return 0

    elif action == "export":
        mask = not getattr(args, "unmask_secrets", False)
        output_file = getattr(args, "output", None)
        exported = cm.export_config(mask_secrets=mask)
        if output_file:
            p = Path(output_file).expanduser().resolve()
            p.write_text(exported, encoding="utf-8")
            print(f"Configuration exported to '{p}' (secrets {'masked' if mask else 'unmasked'}).")
        else:
            print(exported)
        return 0

    elif action == "import":
        input_file = getattr(args, "input", None)
        if not input_file:
            sys.stderr.write("Error: --input <path> is required for config import.\n")
            return 1
        try:
            cm.import_config(input_file, backup_existing=True)
            print(f"Configuration successfully imported from '{input_file}' to '{cm.config_path}'.")
            return 0
        except Exception as e:
            sys.stderr.write(f"Configuration import FAILED: {e}\n")
            return 1

    elif action == "migrate":
        target_ver = getattr(args, "target_version", "0.3.0")
        try:
            success = cm.migrate_config(target_version=target_ver)
            if success:
                print(f"Configuration successfully migrated to version {target_ver}.")
                return 0
            else:
                sys.stderr.write(f"Configuration file not found at {cm.config_path}\n")
                return 1
        except Exception as e:
            sys.stderr.write(f"Configuration migration FAILED: {e}\n")
            return 1

    else:
        sys.stderr.write(
            "Error: Subcommand action required (validate, diff, export, import, migrate).\n"
        )
        return 1
