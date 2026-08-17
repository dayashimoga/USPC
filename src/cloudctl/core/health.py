"""System health diagnosis and status evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cloudctl.core.container import ContainerManager, ContainerStatus
from cloudctl.core.logging import get_logger
from cloudctl.core.storage import StorageManager
from cloudctl.utils.fs import get_free_disk_space_gb

logger = get_logger("health")


@dataclass
class DiagnosticCheck:
    """Individual health check evaluation."""

    component: str
    name: str
    status: str  # HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
    message: str
    remediation: str | None = None


@dataclass
class SystemHealthReport:
    """Aggregated health report."""

    overall_status: str  # HEALTHY, DEGRADED, UNHEALTHY
    checks: list[DiagnosticCheck]
    containers: list[ContainerStatus]


class HealthChecker:
    """Conducts full diagnostic health checks across runtime, services, storage, and networking."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.storage_mgr = StorageManager(
            data_path=config.get("storage", {}).get("data_path", "~/.uspc/data"),
            config_path=config.get("storage", {}).get("config_path", "~/.uspc/config"),
            min_free_space_gb=config.get("storage", {}).get("min_free_space_gb", 20.0),
        )
        self.container_mgr = ContainerManager(
            engine=config.get("runtime", {}).get("engine", "auto")
        )

    def run_all_checks(self) -> SystemHealthReport:
        """Run all diagnostic checks."""
        checks: list[DiagnosticCheck] = []

        # 1. Container Engine
        if self.container_mgr.is_available():
            checks.append(
                DiagnosticCheck(
                    component="Runtime",
                    name="Container Engine",
                    status="HEALTHY",
                    message=f"{self.container_mgr.engine.capitalize()} is responsive ({self.container_mgr.get_version()})",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    component="Runtime",
                    name="Container Engine",
                    status="UNHEALTHY",
                    message=f"{self.container_mgr.engine.capitalize()} daemon/engine is not responding",
                    remediation="Ensure Podman or Docker daemon is started.",
                )
            )

        # 2. Containers status
        expected_containers = ["uspc-nextcloud", "uspc-postgres", "uspc-redis", "uspc-headscale"]
        if self.config.get("media", {}).get("enabled", True):
            expected_containers.append("uspc-media")

        container_statuses: list[ContainerStatus] = []
        for c_name in expected_containers:
            c_stat = self.container_mgr.get_container_status(c_name)
            container_statuses.append(c_stat)
            if c_stat.status == "running":
                checks.append(
                    DiagnosticCheck(
                        component="Services",
                        name=f"Container: {c_name}",
                        status="HEALTHY",
                        message=f"Running (Image: {c_stat.image})",
                    )
                )
            elif c_stat.status == "stopped":
                checks.append(
                    DiagnosticCheck(
                        component="Services",
                        name=f"Container: {c_name}",
                        status="DEGRADED",
                        message="Container is stopped",
                        remediation=f"Run: cloudctl start or {self.container_mgr.engine} start {c_name}",
                    )
                )
            else:
                checks.append(
                    DiagnosticCheck(
                        component="Services",
                        name=f"Container: {c_name}",
                        status="UNHEALTHY",
                        message=f"Status: {c_stat.status}",
                        remediation=f"Check logs: cloudctl logs -s {c_name}",
                    )
                )

        # 3. Storage
        paths = self.storage_mgr.get_paths()
        try:
            free_gb = get_free_disk_space_gb(paths.base_data)
            min_gb = self.storage_mgr.min_free_space_gb
            if free_gb >= min_gb:
                checks.append(
                    DiagnosticCheck(
                        component="Storage",
                        name="Disk Capacity",
                        status="HEALTHY",
                        message=f"{free_gb:.1f} GB free (Minimum required: {min_gb:.1f} GB)",
                    )
                )
            else:
                checks.append(
                    DiagnosticCheck(
                        component="Storage",
                        name="Disk Capacity",
                        status="UNHEALTHY",
                        message=f"Low disk space: {free_gb:.1f} GB free (Required: {min_gb:.1f} GB)",
                        remediation="Free up disk space on host filesystem.",
                    )
                )
        except Exception as e:
            checks.append(
                DiagnosticCheck(
                    component="Storage",
                    name="Disk Capacity",
                    status="UNHEALTHY",
                    message=f"Could not inspect storage capacity: {e}",
                )
            )

        # Overall calculation
        has_unhealthy = any(c.status == "UNHEALTHY" for c in checks)
        has_degraded = any(c.status == "DEGRADED" for c in checks)
        if has_unhealthy:
            overall = "UNHEALTHY"
        elif has_degraded:
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        return SystemHealthReport(
            overall_status=overall,
            checks=checks,
            containers=container_statuses,
        )
