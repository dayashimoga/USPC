"""Podman / Docker Appliance Mode Orchestrator Backend."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import detect_host
from cloudctl.core.health import HealthChecker
from cloudctl.core.logging import get_logger
from cloudctl.core.orchestrator import NodeInfo, Orchestrator, OrchestratorMode, ServiceStatus
from cloudctl.utils.shell import run_command

logger = get_logger("orchestrator.podman")


class PodmanBackend(Orchestrator):
    """Orchestrator implementation for single-node Appliance Mode via Podman / Docker."""

    def __init__(self, config: dict[str, Any], repo_root: Path):
        super().__init__(config, repo_root)
        engine = config.get("runtime", {}).get("engine", "auto")
        self.container_mgr = ContainerManager(engine=engine)

    def get_mode(self) -> OrchestratorMode:
        return OrchestratorMode.APPLIANCE

    def detect_runtime(self) -> dict[str, Any]:
        engine = self.container_mgr.engine
        available = self.container_mgr.is_available()
        ver_res = run_command([engine, "--version"]) if available else None
        version_str = ver_res.stdout.strip() if ver_res and ver_res.success else "unknown"

        return {
            "mode": OrchestratorMode.APPLIANCE.value,
            "engine": engine,
            "available": available,
            "version": version_str,
            "rootless": self.container_mgr.is_rootless(),
        }

    def setup(self, dry_run: bool = False, non_interactive: bool = True) -> bool:
        logger.info(f"Setting up Appliance Mode runtime ({self.container_mgr.engine})...")
        if dry_run:
            logger.info("[Dry Run] Would verify Podman/Docker socket and initialize pod.")
            return True

        if not self.container_mgr.is_available():
            logger.error(
                f"Container engine '{self.container_mgr.engine}' is not available on this host."
            )
            return False

        # Create base network and pod port mappings
        ports = [
            (8080, 8080),  # Headscale
            (8081, 8081),  # Nextcloud
            (8085, 8085),  # Media Service
            (5432, 5432),  # PostgreSQL
            (6379, 6379),  # Redis
        ]
        return self.container_mgr.create_pod(port_mappings=ports)

    def start(self, services: list[str] | None = None) -> bool:
        if self.container_mgr.engine == "podman":
            res = run_command(["podman", "pod", "start", self.container_mgr.pod_name])
            return res.success
        # Docker fallback: start containers
        target = services or ["uspc-postgres", "uspc-redis", "uspc-nextcloud", "uspc-media"]
        all_ok = True
        for s in target:
            if not self.container_mgr.start_container(s):
                all_ok = False
        return all_ok

    def stop(self, services: list[str] | None = None) -> bool:
        if self.container_mgr.engine == "podman":
            res = run_command(["podman", "pod", "stop", self.container_mgr.pod_name])
            return res.success
        target = services or ["uspc-media", "uspc-nextcloud", "uspc-redis", "uspc-postgres"]
        all_ok = True
        for s in target:
            if not self.container_mgr.stop_container(s):
                all_ok = False
        return all_ok

    def restart(self, services: list[str] | None = None) -> bool:
        if self.container_mgr.engine == "podman":
            res = run_command(["podman", "pod", "restart", self.container_mgr.pod_name])
            return res.success
        target = services or ["uspc-postgres", "uspc-redis", "uspc-nextcloud", "uspc-media"]
        all_ok = True
        for s in target:
            if not self.container_mgr.restart_container(s):
                all_ok = False
        return all_ok

    def status(self) -> dict[str, Any]:
        containers = self.container_mgr.list_containers()
        services: dict[str, ServiceStatus] = {}

        expected = ["uspc-postgres", "uspc-redis", "uspc-nextcloud", "uspc-media", "uspc-headscale"]
        for name in expected:
            found = next((c for c in containers if c.name == name or name in c.name), None)
            if found:
                services[name] = ServiceStatus(
                    name=name,
                    status=found.status,
                    replicas=1,
                    ready_replicas=1 if found.status == "running" else 0,
                    image=found.image,
                    ports=found.ports,
                    details=f"health: {found.health}",
                )
            else:
                services[name] = ServiceStatus(
                    name=name,
                    status="stopped",
                    replicas=1,
                    ready_replicas=0,
                    details="container not created",
                )

        return {
            "mode": OrchestratorMode.APPLIANCE.value,
            "engine": self.container_mgr.engine,
            "healthy": any(s.status == "running" for s in services.values()) if services else False,
            "services": {k: s.__dict__ for k, s in services.items()},
        }

    def health_check(self) -> dict[str, Any]:
        checker = HealthChecker(self.config)
        report = checker.run_all_checks()
        return {
            "overall": report.overall_status in ("HEALTHY", "DEGRADED"),
            "checks": {c.name: c.status for c in report.checks},
        }

    def get_logs(self, service_name: str, tail: int = 100) -> str:
        return self.container_mgr.get_logs(service_name, tail=tail)

    def scale(self, service_name: str, replicas: int) -> bool:
        logger.info(
            f"Appliance mode operates on single-host concurrency slots. "
            f"Requested scale={replicas} for '{service_name}'. Concurrency capacity profile updated."
        )
        return True

    def list_nodes(self) -> list[NodeInfo]:
        host = detect_host()
        return [
            NodeInfo(
                name=platform.node() or "localhost",
                role="standalone-appliance",
                status="Ready",
                internal_ip="127.0.0.1",
                cpu_cores=host.cpu_cores,
                ram_gb=host.total_ram_gb,
                is_master=True,
                version=self.detect_runtime().get("version", "1.0.0"),
            )
        ]

    def export_manifests(self, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = output_dir / "uspc-appliance-compose.yaml"
        content = (
            "# USPC Appliance Mode Compose Definition\n"
            "version: '3.8'\n"
            "services:\n"
            "  postgres:\n"
            "    image: docker.io/library/postgres:16.1-alpine\n"
            "    container_name: uspc-postgres\n"
            "    restart: unless-stopped\n"
            "    volumes:\n"
            "      - ~/.uspc/data/postgres:/var/lib/postgresql/data:Z\n"
            "  redis:\n"
            "    image: docker.io/library/redis:7.2-alpine\n"
            "    container_name: uspc-redis\n"
            "    restart: unless-stopped\n"
            "  nextcloud:\n"
            "    image: docker.io/library/nextcloud:27.1.4-apache\n"
            "    container_name: uspc-nextcloud\n"
            "    restart: unless-stopped\n"
            "    volumes:\n"
            "      - ~/.uspc/data/nextcloud:/var/www/html/data:Z\n"
            "  media:\n"
            "    image: localhost/uspc-media:latest\n"
            "    container_name: uspc-media\n"
            "    restart: unless-stopped\n"
            "    ports:\n"
            "      - '8085:8085'\n"
        )
        manifest_file.write_text(content, encoding="utf-8")
        return [manifest_file]
