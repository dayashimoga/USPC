"""CLI command handler for orchestrator management (Podman Appliance vs K3s Cluster)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cloudctl.core.config import ConfigManager, get_repo_root
from cloudctl.core.logging import get_logger
from cloudctl.core.orchestrator import OrchestratorMode, create_orchestrator

logger = get_logger("cmd.orchestrator")


def execute_orchestrator_cmd(args: argparse.Namespace) -> int:
    """Dispatch orchestrator management subcommands."""
    repo_root = get_repo_root()
    cfg_mgr = ConfigManager(config_path=getattr(args, "config", None))
    config = cfg_mgr.load_config()
    orch = create_orchestrator(config, repo_root=repo_root)

    sub = getattr(args, "orchestrator_subcommand", "status")

    if sub == "status":
        status_data = orch.status()
        runtime_data = orch.detect_runtime()
        combined = {
            "mode": orch.get_mode().value,
            "runtime": runtime_data,
            "status": status_data,
        }
        if getattr(args, "json", False):
            print(json.dumps(combined, indent=2))
        else:
            print("=" * 60)
            print(f" USPC Orchestrator: {orch.get_mode().value.upper()} MODE")
            print("=" * 60)
            print(f" Engine   : {runtime_data.get('engine', 'unknown')}")
            print(f" Version  : {runtime_data.get('version', 'unknown')}")
            print(f" Available: {'Yes' if runtime_data.get('available') else 'No'}")
            print(f" Healthy  : {'Yes' if status_data.get('healthy') else 'No'}")
            print("\nServices:")
            services = status_data.get("services", {})
            if services:
                for sname, sinfo in services.items():
                    st = sinfo.get("status", "unknown")
                    reps = f"{sinfo.get('ready_replicas', 0)}/{sinfo.get('replicas', 1)}"
                    print(f"  * {sname:<18} [{st.upper():<7}] (Replicas: {reps})")
            else:
                print("  (No active services detected)")
        return 0

    elif sub == "switch":
        target_mode = args.mode.lower()
        if target_mode not in (
            OrchestratorMode.APPLIANCE.value,
            OrchestratorMode.CLUSTER.value,
            "k3s",
        ):
            print(f"Error: Invalid mode '{target_mode}'. Choose 'appliance' or 'cluster'.")
            return 1

        normalized_mode = (
            OrchestratorMode.CLUSTER.value
            if target_mode in ("cluster", "k3s")
            else OrchestratorMode.APPLIANCE.value
        )
        config.setdefault("orchestrator", {})["mode"] = normalized_mode

        # Save config
        cfg_mgr.save_config(config)

        print(f"[OK] Successfully switched USPC orchestrator to '{normalized_mode}' mode.")
        print(f"Configuration written to: {cfg_mgr.config_path}")
        print("Run 'cloudctl setup' or 'cloudctl orchestrator setup' to reconcile workloads.")
        return 0

    elif sub == "nodes":
        nodes = orch.list_nodes()
        if getattr(args, "json", False):
            print(json.dumps([n.__dict__ for n in nodes], indent=2))
        else:
            print("=" * 70)
            print(f" USPC Orchestrator Nodes ({orch.get_mode().value.upper()} Mode)")
            print("=" * 70)
            for n in nodes:
                role_str = "Control-Plane / Master" if n.is_master else n.role
                print(f" * Node     : {n.name}")
                print(f"   Role     : {role_str}")
                print(f"   Status   : {n.status}")
                print(f"   IP       : {n.internal_ip}")
                print(f"   Resources: {n.cpu_cores} Cores, {n.ram_gb} GB RAM")
                print(f"   Version  : {n.version or 'N/A'}")
                print()
        return 0

    elif sub == "scale":
        service = args.service
        replicas = args.replicas
        success = orch.scale(service, replicas)
        if success:
            print(
                f"[OK] Scaled '{service}' to {replicas} replicas in {orch.get_mode().value} mode."
            )
            return 0
        else:
            print(f"Error: Failed to scale service '{service}'.")
            return 1

    elif sub == "manifests":
        out_dir = Path(getattr(args, "output_dir", "deploy/manifests_export")).resolve()
        exported = orch.export_manifests(out_dir)
        print(f"[OK] Exported {len(exported)} declarative manifest(s) to: {out_dir}")
        for p in exported:
            print(f"  -> {p.name}")
        return 0

    print(f"Unknown subcommand: {sub}")
    return 1
