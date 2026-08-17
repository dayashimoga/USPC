"""K3s / Kubernetes Cluster Mode Orchestrator Backend."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from cloudctl.core.logging import get_logger
from cloudctl.core.orchestrator import NodeInfo, Orchestrator, OrchestratorMode, ServiceStatus
from cloudctl.utils.shell import run_command

logger = get_logger("orchestrator.k3s")


class K3sBackend(Orchestrator):
    """Orchestrator backend for multi-node K3s / CNCF Kubernetes clusters."""

    def __init__(self, config: dict[str, Any], repo_root: Path):
        super().__init__(config, repo_root)
        self.namespace = config.get("orchestrator", {}).get("namespace", "uspc")
        self.k3s_bin = shutil.which("k3s") or "k3s"
        self.kubectl_bin = shutil.which("kubectl") or (
            f"{self.k3s_bin} kubectl" if shutil.which("k3s") else "kubectl"
        )
        self.kubeconfig = Path("~/.kube/config").expanduser()

    def get_mode(self) -> OrchestratorMode:
        return OrchestratorMode.CLUSTER

    def detect_runtime(self) -> dict[str, Any]:
        has_k3s = shutil.which("k3s") is not None
        has_kubectl = shutil.which("kubectl") is not None or has_k3s
        version_str = "not-installed"

        if has_kubectl:
            cmd = (
                ["kubectl", "version", "--client", "-o", "json"]
                if shutil.which("kubectl")
                else ["k3s", "kubectl", "version", "--client", "-o", "json"]
            )
            res = run_command(cmd)
            if res.success:
                try:
                    data = json.loads(res.stdout)
                    version_str = data.get("clientVersion", {}).get("gitVersion", "unknown")
                except Exception:
                    version_str = res.stdout.strip()

        return {
            "mode": OrchestratorMode.CLUSTER.value,
            "engine": "k3s",
            "available": has_k3s or has_kubectl,
            "version": version_str,
            "namespace": self.namespace,
            "has_k3s_service": has_k3s,
        }

    def _run_kubectl(self, args: list[str]) -> Any:
        if shutil.which("kubectl"):
            cmd = ["kubectl"] + args
        elif shutil.which("k3s"):
            cmd = ["k3s", "kubectl"] + args
        else:
            return run_command(["kubectl"] + args)
        return run_command(cmd)

    def setup(self, dry_run: bool = False, non_interactive: bool = True) -> bool:
        logger.info("Initializing USPC K3s Cluster Mode...")
        if dry_run:
            logger.info(
                "[Dry Run] Would apply Kubernetes manifests from deploy/k3s/ into namespace 'uspc'."
            )
            return True

        # Ensure namespace exists
        ns_res = self._run_kubectl(
            ["create", "namespace", self.namespace, "--dry-run=client", "-o", "yaml"]
        )
        if ns_res.success:
            self._run_kubectl(["apply", "-f", "-"], env={"STDIN": ns_res.stdout})

        # Apply manifests from deploy/k3s
        manifests_dir = self.repo_root / "deploy" / "k3s"
        if manifests_dir.exists():
            return self.apply_manifests(manifests_dir)

        logger.warning(
            f"K3s manifests directory '{manifests_dir}' not found. Generating default manifests."
        )
        return True

    def apply_manifests(self, manifest_dir: Path) -> bool:
        """Apply all YAML manifests in directory to K3s cluster."""
        res = self._run_kubectl(["apply", "-n", self.namespace, "-f", str(manifest_dir)])
        return res.success

    def start(self, services: list[str] | None = None) -> bool:
        target = services or ["nextcloud", "postgres", "redis", "uspc-media"]
        all_ok = True
        for s in target:
            res = self._run_kubectl(
                ["scale", "-n", self.namespace, f"deployment/{s}", "--replicas=1"]
            )
            if not res.success:
                all_ok = False
        return all_ok

    def stop(self, services: list[str] | None = None) -> bool:
        target = services or ["nextcloud", "postgres", "redis", "uspc-media"]
        all_ok = True
        for s in target:
            res = self._run_kubectl(
                ["scale", "-n", self.namespace, f"deployment/{s}", "--replicas=0"]
            )
            if not res.success:
                all_ok = False
        return all_ok

    def restart(self, services: list[str] | None = None) -> bool:
        target = services or ["nextcloud", "postgres", "redis", "uspc-media"]
        all_ok = True
        for s in target:
            res = self._run_kubectl(["rollout", "restart", "-n", self.namespace, f"deployment/{s}"])
            if not res.success:
                all_ok = False
        return all_ok

    def status(self) -> dict[str, Any]:
        res = self._run_kubectl(["get", "pods", "-n", self.namespace, "-o", "json"])
        services: dict[str, ServiceStatus] = {}

        if res.success:
            try:
                data = json.loads(res.stdout)
                for item in data.get("items", []):
                    pod_name = item.get("metadata", {}).get("name", "unknown")
                    phase = item.get("status", {}).get("phase", "Unknown")
                    app_label = item.get("metadata", {}).get("labels", {}).get("app", pod_name)

                    services[app_label] = ServiceStatus(
                        name=app_label,
                        status="running" if phase == "Running" else phase.lower(),
                        replicas=1,
                        ready_replicas=1 if phase == "Running" else 0,
                        details=f"pod: {pod_name}, phase: {phase}",
                    )
            except Exception as exc:
                logger.error(f"Failed to parse Kubernetes pod status: {exc}")

        return {
            "mode": OrchestratorMode.CLUSTER.value,
            "engine": "k3s",
            "namespace": self.namespace,
            "healthy": any(s.status == "running" for s in services.values()) if services else False,
            "services": {k: s.__dict__ for k, s in services.items()},
        }

    def health_check(self) -> dict[str, Any]:
        res = self._run_kubectl(["get", "endpoints", "-n", self.namespace, "-o", "json"])
        healthy_endpoints = {}

        if res.success:
            try:
                data = json.loads(res.stdout)
                for item in data.get("items", []):
                    ep_name = item.get("metadata", {}).get("name", "unknown")
                    subsets = item.get("subsets", [])
                    has_ready = any(bool(sub.get("addresses")) for sub in subsets)
                    healthy_endpoints[ep_name] = "healthy" if has_ready else "degraded"
            except Exception:
                pass

        return {
            "overall": all(v == "healthy" for v in healthy_endpoints.values())
            if healthy_endpoints
            else False,
            "endpoints": healthy_endpoints,
        }

    def get_logs(self, service_name: str, tail: int = 100) -> str:
        res = self._run_kubectl(
            ["logs", "-n", self.namespace, f"deployment/{service_name}", f"--tail={tail}"]
        )
        return res.stdout if res.success else res.stderr

    def scale(self, service_name: str, replicas: int) -> bool:
        logger.info(f"Scaling Kubernetes deployment '{service_name}' to {replicas} replicas...")
        res = self._run_kubectl(
            ["scale", "-n", self.namespace, f"deployment/{service_name}", f"--replicas={replicas}"]
        )
        return res.success

    def list_nodes(self) -> list[NodeInfo]:
        res = self._run_kubectl(["get", "nodes", "-o", "json"])
        nodes: list[NodeInfo] = []

        if res.success:
            try:
                data = json.loads(res.stdout)
                for item in data.get("items", []):
                    name = item.get("metadata", {}).get("name", "node")
                    labels = item.get("metadata", {}).get("labels", {})
                    is_master = (
                        "node-role.kubernetes.io/master" in labels
                        or "node-role.kubernetes.io/control-plane" in labels
                    )
                    role = "server" if is_master else "agent"

                    status_conds = item.get("status", {}).get("conditions", [])
                    ready_cond = next((c for c in status_conds if c.get("type") == "Ready"), {})
                    status = "Ready" if ready_cond.get("status") == "True" else "NotReady"

                    addrs = item.get("status", {}).get("addresses", [])
                    ip = next(
                        (a.get("address") for a in addrs if a.get("type") == "InternalIP"),
                        "127.0.0.1",
                    )

                    cap = item.get("status", {}).get("capacity", {})
                    cpu = int(cap.get("cpu", "1"))
                    ram_str = cap.get("memory", "1048576Ki").replace("Ki", "")
                    ram_gb = round(float(ram_str) / (1024 * 1024), 2) if ram_str.isdigit() else 2.0

                    ver = item.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "")

                    nodes.append(
                        NodeInfo(
                            name=name,
                            role=role,
                            status=status,
                            internal_ip=ip,
                            cpu_cores=cpu,
                            ram_gb=ram_gb,
                            is_master=is_master,
                            version=ver,
                        )
                    )
            except Exception as exc:
                logger.error(f"Failed parsing K3s node list: {exc}")

        return nodes

    def export_manifests(self, output_dir: Path) -> list[Path]:
        src_dir = self.repo_root / "deploy" / "k3s"
        output_dir.mkdir(parents=True, exist_ok=True)
        copied: list[Path] = []

        if src_dir.exists():
            for f in src_dir.glob("*.yaml"):
                dest = output_dir / f.name
                dest.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                copied.append(dest)

        return copied
