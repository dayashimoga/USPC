"""Abstract base interface and factory for container orchestration backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from cloudctl.core.logging import get_logger

logger = get_logger("orchestrator")


class OrchestratorMode(str, Enum):
    """Supported orchestration operating modes."""

    APPLIANCE = "appliance"  # Default: Single-node rootless Podman/Docker
    CLUSTER = "cluster"  # Multi-node: Declarative K3s/Kubernetes


@dataclass
class ServiceStatus:
    """Status record for an individual orchestrated microservice."""

    name: str
    status: str  # running, stopped, degraded, error, unknown
    replicas: int = 1
    ready_replicas: int = 1
    image: str = ""
    ports: list[str] = field(default_factory=list)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    details: str = ""


@dataclass
class NodeInfo:
    """Status and role details for a cluster node."""

    name: str
    role: str  # server (control-plane), agent (worker)
    status: str  # Ready, NotReady, SchedulingDisabled
    internal_ip: str
    cpu_cores: int
    ram_gb: float
    is_master: bool = False
    version: str = ""


class Orchestrator(ABC):
    """Abstract orchestrator interface implemented by Podman and K3s backends."""

    def __init__(self, config: dict[str, Any], repo_root: Path):
        self.config = config
        self.repo_root = repo_root

    @abstractmethod
    def get_mode(self) -> OrchestratorMode:
        """Return the active orchestrator mode."""
        pass

    @abstractmethod
    def detect_runtime(self) -> dict[str, Any]:
        """Detect and return installed runtime binaries, versions, and capabilities."""
        pass

    @abstractmethod
    def setup(self, dry_run: bool = False, non_interactive: bool = True) -> bool:
        """Initialize the orchestration runtime, networks, secrets, and volumes."""
        pass

    @abstractmethod
    def start(self, services: list[str] | None = None) -> bool:
        """Start all or specified workloads."""
        pass

    @abstractmethod
    def stop(self, services: list[str] | None = None) -> bool:
        """Stop all or specified workloads gracefully."""
        pass

    @abstractmethod
    def restart(self, services: list[str] | None = None) -> bool:
        """Restart all or specified workloads."""
        pass

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return structured runtime and per-service health status."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Run health check against all orchestrated endpoints."""
        pass

    @abstractmethod
    def get_logs(self, service_name: str, tail: int = 100) -> str:
        """Fetch log output for a given microservice."""
        pass

    @abstractmethod
    def scale(self, service_name: str, replicas: int) -> bool:
        """Scale service replicas (horizontal scaling in cluster mode)."""
        pass

    @abstractmethod
    def list_nodes(self) -> list[NodeInfo]:
        """List active nodes in the orchestration environment."""
        pass

    @abstractmethod
    def export_manifests(self, output_dir: Path) -> list[Path]:
        """Generate and export declarative orchestration manifests."""
        pass


def create_orchestrator(config: dict[str, Any], repo_root: Path | None = None) -> Orchestrator:
    """Factory creating the configured Orchestrator backend (Podman Appliance or K3s Cluster)."""
    if repo_root is None:
        from cloudctl.core.config import get_repo_root

        repo_root = get_repo_root()

    orch_cfg = config.get("orchestrator", {})
    mode_str = orch_cfg.get("mode", "appliance").lower()

    if mode_str == OrchestratorMode.CLUSTER.value or mode_str == "k3s":
        from cloudctl.core.backends.k3s_backend import K3sBackend

        return K3sBackend(config=config, repo_root=repo_root)

    from cloudctl.core.backends.podman_backend import PodmanBackend

    return PodmanBackend(config=config, repo_root=repo_root)
