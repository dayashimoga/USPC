"""Container engine abstraction supporting Podman and Docker."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from cloudctl.core.logging import get_logger
from cloudctl.utils.shell import CommandResult, run_command

logger = get_logger("container")


@dataclass
class ContainerStatus:
    """Status information for a single container."""

    name: str
    id: str
    image: str
    status: str  # running, exited, created, paused, unknown
    health: str  # healthy, unhealthy, starting, none
    ports: list[str]
    created_at: str


class ContainerManager:
    """Abstracts Podman (preferred) and Docker container management."""

    def __init__(self, engine: str = "auto"):
        self.engine = self._resolve_engine(engine)
        self.pod_name = "uspc-pod"

    def _resolve_engine(self, engine: str) -> str:
        """Find executable container runtime."""
        if engine in ("podman", "docker"):
            if shutil.which(engine):
                return engine
            logger.warning(f"Requested engine '{engine}' not found on PATH, probing alternatives.")

        # Auto-detect: prefer Podman
        if shutil.which("podman"):
            return "podman"
        if shutil.which("docker"):
            return "docker"

        logger.debug(
            "No active container engine binary found on host (may be running in simulation/isolated mode)"
        )
        return "docker"

    def is_available(self) -> bool:
        """Check if container engine daemon/CLI is responsive."""
        res = run_command([self.engine, "info"], timeout=10.0)
        return res.success

    def get_version(self) -> str:
        """Get container engine version."""
        res = run_command([self.engine, "--version"], timeout=5.0)
        if res.success:
            return res.stdout.strip()
        return "unknown"

    def create_pod(self, port_mappings: list[tuple[int, int]] | None = None) -> bool:
        """Create a shared network Pod (Podman) or bridge network (Docker)."""
        if self.engine == "podman":
            # Check if pod exists
            check = run_command(["podman", "pod", "exists", self.pod_name], timeout=5.0)
            if check.success:
                logger.debug(f"Podman pod '{self.pod_name}' already exists.")
                return True

            cmd = ["podman", "pod", "create", "--name", self.pod_name]
            if port_mappings:
                for host_p, cont_p in port_mappings:
                    cmd.extend(["-p", f"{host_p}:{cont_p}"])
            res = run_command(cmd, timeout=30.0)
            return res.success
        else:
            # Docker network
            check = run_command(["docker", "network", "inspect", "uspc-net"], timeout=5.0)
            if check.success:
                return True
            res = run_command(["docker", "network", "create", "uspc-net"], timeout=30.0)
            return res.success

    def run_container(
        self,
        name: str,
        image: str,
        env: dict[str, str] | None = None,
        volumes: list[tuple[str, str]] | None = None,
        ports: list[tuple[int, int]] | None = None,
        restart_policy: str = "unless-stopped",
        extra_args: list[str] | None = None,
    ) -> bool:
        """Run a container with pinned version, volumes, and restart policy."""
        # Stop and remove existing container with same name if present
        self.remove_container(name, force=True)

        cmd = [self.engine, "run", "-d", "--name", name, f"--restart={restart_policy}"]

        # Network / Pod assignment
        if self.engine == "podman":
            cmd.extend(["--pod", self.pod_name])
        else:
            cmd.extend(["--network", "uspc-net"])
            if ports:
                for host_p, cont_p in ports:
                    cmd.extend(["-p", f"{host_p}:{cont_p}"])

        # Environment variables
        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])

        # Persistent volume mounts
        if volumes:
            for host_dir, cont_dir in volumes:
                cmd.extend(["-v", f"{host_dir}:{cont_dir}:Z"])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(image)

        logger.info(f"Launching container '{name}' with image '{image}'")
        res = run_command(cmd, timeout=60.0)
        if not res.success:
            logger.error(f"Failed to start container {name}: {res.stderr}")
            return False
        return True

    def stop_container(self, name: str, timeout: int = 15) -> bool:
        """Stop running container."""
        res = run_command([self.engine, "stop", "-t", str(timeout), name], timeout=timeout + 10.0)
        return res.success

    def start_container(self, name: str) -> bool:
        """Start existing stopped container."""
        res = run_command([self.engine, "start", name], timeout=30.0)
        return res.success

    def restart_container(self, name: str, timeout: int = 15) -> bool:
        """Restart container."""
        res = run_command(
            [self.engine, "restart", "-t", str(timeout), name], timeout=timeout + 10.0
        )
        return res.success

    def remove_container(self, name: str, force: bool = True) -> bool:
        """Remove container."""
        cmd = [self.engine, "rm"]
        if force:
            cmd.append("-f")
        cmd.append(name)
        res = run_command(cmd, timeout=30.0)
        return res.success

    def inspect_container(self, name: str) -> dict[str, Any] | None:
        """Inspect container configuration and runtime state."""
        res = run_command([self.engine, "inspect", name], timeout=10.0)
        if res.success and res.stdout.strip():
            try:
                data = json.loads(res.stdout)
                return data[0] if isinstance(data, list) and data else None
            except Exception:
                pass
        return None

    def get_container_status(self, name: str) -> ContainerStatus:
        """Query standardized status for a container."""
        info = self.inspect_container(name)
        if not info:
            return ContainerStatus(
                name=name,
                id="",
                image="",
                status="stopped",
                health="none",
                ports=[],
                created_at="",
            )

        state = info.get("State", {})
        status = state.get("Status", "unknown")
        health_info = state.get("Health", {})
        health = health_info.get("Status", "none") if health_info else "none"
        image = info.get("Config", {}).get("Image", "")
        cid = info.get("Id", "")[:12]
        created = info.get("Created", "")

        return ContainerStatus(
            name=name,
            id=cid,
            image=image,
            status=status,
            health=health,
            ports=[],
            created_at=created,
        )

    def get_logs(self, name: str, tail: int = 100) -> str:
        """Retrieve recent logs for a container."""
        res = run_command([self.engine, "logs", "--tail", str(tail), name], timeout=15.0)
        return (res.stdout + res.stderr).strip()

    def exec_command(
        self, name: str, cmd: Sequence[str] | str, user: str | None = None
    ) -> CommandResult:
        """Execute command inside a running container."""
        exec_cmd = [self.engine, "exec"]
        if user:
            exec_cmd.extend(["-u", user])
        exec_cmd.append(name)
        if isinstance(cmd, str):
            exec_cmd.extend(["sh", "-c", cmd])
        else:
            exec_cmd.extend(cmd)

        return run_command(exec_cmd, timeout=60.0)
