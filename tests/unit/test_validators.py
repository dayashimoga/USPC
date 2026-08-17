"""Unit tests for validator utilities."""

from pathlib import Path

import pytest

from cloudctl.utils.validators import (
    is_safe_path,
    is_valid_cidr,
    is_valid_cloud_name,
    is_valid_domain,
    is_valid_ip,
    is_valid_port,
    is_valid_username,
    parse_memory_mb,
)


def test_port_validator():
    assert is_valid_port(80) is True
    assert is_valid_port(8080) is True
    assert is_valid_port("443") is True
    assert is_valid_port(65535) is True
    assert is_valid_port(0) is False
    assert is_valid_port(70000) is False
    assert is_valid_port("invalid") is False
    assert is_valid_port(None) is False


def test_ip_validator():
    assert is_valid_ip("127.0.0.1") is True
    assert is_valid_ip("100.64.0.1") is True
    assert is_valid_ip("::1") is True
    assert is_valid_ip("999.999.999.999") is False
    assert is_valid_ip("not-an-ip") is False
    assert is_valid_ip(123) is False


def test_cidr_validator():
    assert is_valid_cidr("100.64.0.0/10") is True
    assert is_valid_cidr("192.168.1.0/24") is True
    assert is_valid_cidr("10.0.0.0/8") is True
    assert is_valid_cidr("invalid-cidr") is False
    assert is_valid_cidr(None) is False


def test_domain_validator():
    assert is_valid_domain("mycloud.local") is True
    assert is_valid_domain("cloud.example.com") is True
    assert is_valid_domain("localhost") is True
    assert is_valid_domain("-invalid.com") is False
    assert is_valid_domain("invalid-.com") is False
    assert is_valid_domain("") is False
    assert is_valid_domain(None) is False


def test_username_and_cloud_name():
    assert is_valid_username("admin") is True
    assert is_valid_username("user_123") is True
    assert is_valid_username("admin@domain.com") is True
    assert is_valid_username("ab") is False  # Too short
    assert is_valid_username("invalid space") is False

    assert is_valid_cloud_name("my-cloud_01") is True
    assert is_valid_cloud_name("cl") is False
    assert is_valid_cloud_name("invalid*char") is False


def test_parse_memory_mb():
    assert parse_memory_mb(4096) == 4096
    assert parse_memory_mb("1024M") == 1024
    assert parse_memory_mb("2G") == 2048
    assert parse_memory_mb("4GB") == 4096
    assert parse_memory_mb("512MB") == 512
    assert parse_memory_mb("2048") == 2048
    assert parse_memory_mb("1024KB") == 1

    with pytest.raises(ValueError):
        parse_memory_mb("")
    with pytest.raises(ValueError):
        parse_memory_mb("invalid")


def test_is_safe_path(temp_dir: Path):
    base = temp_dir / "base"
    base.mkdir()
    child = base / "sub" / "file.txt"
    outside = temp_dir / "other" / "file.txt"

    assert is_safe_path(base, child) is True
    assert is_safe_path(base, base) is True
    assert is_safe_path(base, outside) is False
