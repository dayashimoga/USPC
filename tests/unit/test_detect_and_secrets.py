"""Unit tests for host detection and secret manager."""

from pathlib import Path

from cloudctl.core.detect import (
    detect_container_engine,
    detect_firewall,
    detect_host,
    detect_os,
    detect_privileges,
    detect_virtualization,
)
from cloudctl.core.secrets import SecretManager


def test_host_detection():
    host = detect_host()
    assert host.os_name in ("linux", "windows", "macos", "unknown")
    assert host.cpu_cores >= 1
    assert host.total_ram_gb > 0
    assert host.container_engine in ("docker", "podman", "none")
    assert isinstance(host.disks, list)


def test_individual_detection_functions():
    os_name, release, version, arch = detect_os()
    assert os_name is not None
    assert arch in ("x86_64", "aarch64", "arm64", "amd64", "x86", "i386")

    privs = detect_privileges(os_name)
    assert isinstance(privs, bool)

    virt = detect_virtualization(os_name)
    assert isinstance(virt, str)

    engine, ver = detect_container_engine()
    assert engine in ("podman", "docker", "none")

    fw, active = detect_firewall(os_name)
    assert isinstance(fw, str)
    assert isinstance(active, bool)


def test_secret_manager(temp_dir: Path):
    sec_dir = temp_dir / "secrets"
    mgr = SecretManager(secrets_dir=sec_dir)

    # Initial generation
    sec1 = mgr.load_or_generate_secrets()
    assert len(sec1.postgres_password) == 32
    assert len(sec1.nextcloud_admin_password) == 32
    assert len(sec1.media_jwt_secret) == 64
    assert mgr.secrets_file.exists()

    # Second load should retrieve existing secrets
    sec2 = mgr.load_or_generate_secrets()
    assert sec2.postgres_password == sec1.postgres_password
    assert sec2.media_jwt_secret == sec1.media_jwt_secret
