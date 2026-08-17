import ctypes
import os
import platform
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psutil

from cloudctl.utils.shell import run_command


@dataclass
class DiskInfo:
    """Block device / filesystem info."""

    mount_point: str
    device: str
    fstype: str
    total_gb: float
    free_gb: float
    is_writable: bool


@dataclass
class HostInfo:
    """Comprehensive host environment and capabilities."""

    os_name: str  # linux, windows, macos
    os_release: str
    os_version: str
    arch: str
    cpu_cores: int
    total_ram_gb: float
    available_ram_gb: float
    is_root_or_admin: bool
    virtualization_type: str  # native, wsl2, hyperv, kvm, podman-machine, none/unknown
    container_engine: str  # podman, docker, none
    engine_version: str
    firewall_type: str  # ufw, firewalld, iptables, windows-firewall, pf, none
    firewall_active: bool
    disks: list[DiskInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def detect_os() -> tuple[str, str, str, str]:
    """Detect OS name (linux/windows/macos), release, version, and architecture."""
    system = platform.system().lower()
    if system == "linux":
        os_name = "linux"
    elif system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    else:
        os_name = system

    release = platform.release()
    version = platform.version()
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        arch = "x86_64"
    elif arch in ("arm64", "aarch64"):
        arch = "aarch64"

    return os_name, release, version, arch


def detect_privileges(os_name: str) -> bool:
    """Check if current process has root/administrator privileges."""
    if os_name == "windows":
        try:
            windll = getattr(ctypes, "windll", None)
            if windll is not None:
                return windll.shell32.IsUserAnAdmin() != 0
            return False
        except Exception:
            return False
    else:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def detect_virtualization(os_name: str) -> str:
    """Detect virtualization environment (WSL2, HyperV, KVM, etc.)."""
    if os_name == "linux":
        # Check WSL
        try:
            if Path("/proc/version").exists():
                content = Path("/proc/version").read_text(encoding="utf-8").lower()
                if "microsoft" in content or "wsl" in content:
                    return "wsl2"
        except Exception:
            pass

        # Check systemd-detect-virt
        res = run_command(["systemd-detect-virt"], timeout=5.0)
        if res.success and res.stdout.strip() and res.stdout.strip() != "none":
            return res.stdout.strip()

        return "native"

    elif os_name == "windows":
        # Check if WSL2 is installed
        wsl_check = run_command(["wsl", "--status"], timeout=5.0)
        if wsl_check.success:
            return "hyperv-wsl2-available"
        return "native-windows"

    elif os_name == "macos":
        return "native-macos"

    return "unknown"


def detect_container_engine() -> tuple[str, str]:
    """Detect available container engine (Podman preferred, Docker fallback)."""
    # Check podman first
    podman_path = shutil.which("podman")
    if podman_path:
        res = run_command([podman_path, "--version"], timeout=5.0)
        if res.success:
            ver = res.stdout.strip().replace("podman version ", "")
            return "podman", ver

    # Fallback to docker
    docker_path = shutil.which("docker")
    if docker_path:
        res = run_command([docker_path, "--version"], timeout=5.0)
        if res.success:
            ver = res.stdout.strip().replace("Docker version ", "")
            return "docker", ver

    return "none", "none"


def detect_firewall(os_name: str) -> tuple[str, bool]:
    """Detect active host firewall software."""
    if os_name == "linux":
        if shutil.which("ufw"):
            res = run_command(["ufw", "status"], timeout=5.0)
            return "ufw", "active" in res.stdout.lower()
        if shutil.which("firewall-cmd"):
            res = run_command(["firewall-cmd", "--state"], timeout=5.0)
            return "firewalld", res.success and "running" in res.stdout.lower()
        if shutil.which("iptables"):
            return "iptables", True
        return "none", False

    elif os_name == "windows":
        res = run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-NetFirewallProfile -Profile Domain,Public,Private).Enabled",
            ],
            timeout=5.0,
        )
        is_active = "True" in res.stdout
        return "windows-firewall", is_active

    elif os_name == "macos":
        res = run_command(["pfctl", "-s", "info"], timeout=5.0)
        return "pf", res.success and "enabled" in res.stdout.lower()

    return "none", False


def detect_disks() -> list[DiskInfo]:
    """Detect mounted disks, filesystems, and free capacities."""
    disks = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                # Check writable
                test_file = Path(part.mountpoint) / ".uspc_write_test"
                is_writable = False
                try:
                    test_file.write_text("ok", encoding="utf-8")
                    test_file.unlink()
                    is_writable = True
                except Exception:
                    is_writable = False

                disks.append(
                    DiskInfo(
                        mount_point=part.mountpoint,
                        device=part.device,
                        fstype=part.fstype,
                        total_gb=round(usage.total / (1024**3), 2),
                        free_gb=round(usage.free / (1024**3), 2),
                        is_writable=is_writable,
                    )
                )
            except Exception:
                continue
    except Exception:
        pass
    return disks


def detect_host() -> HostInfo:
    """Run full host environment discovery."""
    os_name, os_release, os_version, arch = detect_os()
    cpu_cores = os.cpu_count() or 1
    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / (1024**3), 2)
    available_ram_gb = round(mem.available / (1024**3), 2)

    is_admin = detect_privileges(os_name)
    virt_type = detect_virtualization(os_name)
    engine, engine_ver = detect_container_engine()
    fw_type, fw_active = detect_firewall(os_name)
    disks = detect_disks()

    return HostInfo(
        os_name=os_name,
        os_release=os_release,
        os_version=os_version,
        arch=arch,
        cpu_cores=cpu_cores,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        is_root_or_admin=is_admin,
        virtualization_type=virt_type,
        container_engine=engine,
        engine_version=engine_ver,
        firewall_type=fw_type,
        firewall_active=fw_active,
        disks=disks,
    )
