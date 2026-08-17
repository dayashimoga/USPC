"""Comprehensive tests for validation utilities ensuring >95% branch coverage."""

from __future__ import annotations

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


def test_is_valid_port_all_branches():
    # Valid integers and strings
    assert is_valid_port(80)
    assert is_valid_port(443)
    assert is_valid_port(65535)
    assert is_valid_port(1)
    assert is_valid_port("8080")

    # Invalid ports
    assert not is_valid_port(0)
    assert not is_valid_port(-1)
    assert not is_valid_port(65536)
    assert not is_valid_port(100000)
    assert not is_valid_port("invalid_port_string")
    assert not is_valid_port(None)
    assert not is_valid_port([])


def test_is_valid_ip_and_cidr_all_branches():
    # Valid IPs
    assert is_valid_ip("127.0.0.1")
    assert is_valid_ip("192.168.1.100")
    assert is_valid_ip("::1")
    assert is_valid_ip("2001:db8::1")

    # Invalid IPs
    assert not is_valid_ip("")
    assert not is_valid_ip("999.999.999.999")
    assert not is_valid_ip("not an ip")
    assert not is_valid_ip(None)

    # Valid CIDRs
    assert is_valid_cidr("10.0.0.0/8")
    assert is_valid_cidr("100.64.0.0/10")
    assert is_valid_cidr("192.168.1.0/24")
    assert is_valid_cidr("fd7a:115c:a1e0::/48")

    # Invalid CIDRs
    assert not is_valid_cidr("")
    assert not is_valid_cidr("invalid/24")
    assert not is_valid_cidr("300.300.300.300/24")
    assert not is_valid_cidr(None)


def test_is_valid_domain_all_branches():
    assert is_valid_domain("localhost")
    assert is_valid_domain("example.com")
    assert is_valid_domain("my-cloud.sub.domain.org")
    assert is_valid_domain("cloud123.local")

    # Invalid domains
    assert not is_valid_domain("")
    assert not is_valid_domain("a" * 256)
    assert not is_valid_domain("-invalid.com")
    assert not is_valid_domain("invalid-.com")
    assert not is_valid_domain("in valid.com")
    assert not is_valid_domain("http://example.com")
    assert not is_valid_domain(None)


def test_is_valid_username_and_cloud_name():
    assert is_valid_username("admin")
    assert is_valid_username("user_123")
    assert is_valid_username("my-name")

    assert not is_valid_username("")
    assert not is_valid_username("ab")  # min 3 chars
    assert not is_valid_username("a" * 65)  # max 64 chars
    assert not is_valid_username("user space")
    assert not is_valid_username(None)

    assert is_valid_cloud_name("mycloud")
    assert is_valid_cloud_name("uspc-node-01")
    assert not is_valid_cloud_name("")
    assert not is_valid_cloud_name("ab")
    assert not is_valid_cloud_name("cloud*name")
    assert not is_valid_cloud_name("a" * 33)
    assert not is_valid_cloud_name(None)


def test_parse_memory_mb_all_formats():
    assert parse_memory_mb(1024) == 1024
    assert parse_memory_mb("512") == 512
    assert parse_memory_mb("512M") == 512
    assert parse_memory_mb("512MB") == 512
    assert parse_memory_mb("2G") == 2048
    assert parse_memory_mb("4GB") == 4096
    assert parse_memory_mb("1024K") == 1
    assert parse_memory_mb("2048KB") == 2

    with pytest.raises(ValueError):
        parse_memory_mb("invalid")
    with pytest.raises(ValueError):
        parse_memory_mb("")
    with pytest.raises(ValueError):
        parse_memory_mb("-100M")


def test_is_safe_path_boundary_cases(temp_dir: Path):
    base = temp_dir / "safe_root"
    base.mkdir()
    child = base / "child.txt"
    nested = base / "sub" / "leaf.txt"

    assert is_safe_path(base, child)
    assert is_safe_path(base, nested)
    assert is_safe_path(base, base)

    # Path traversal outside base
    outside = temp_dir / "outside.txt"
    assert not is_safe_path(base, outside)
    assert not is_safe_path(base, base / ".." / "outside.txt")
