"""Input validation utilities for USPC configuration and runtime parameters."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path


def is_valid_port(port: int | str) -> bool:
    """Validate TCP/UDP port range (1-65535)."""
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False


def is_valid_ip(ip_str: str) -> bool:
    """Validate IPv4 or IPv6 address string."""
    if not isinstance(ip_str, str):
        return False
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except ValueError:
        return False


def is_valid_cidr(cidr_str: str) -> bool:
    """Validate CIDR network string (e.g., 100.64.0.0/10)."""
    if not isinstance(cidr_str, str):
        return False
    try:
        ipaddress.ip_network(cidr_str.strip(), strict=False)
        return True
    except ValueError:
        return False


def is_valid_domain(domain_str: str) -> bool:
    """Validate FQDN or local hostname."""
    if not isinstance(domain_str, str) or not domain_str.strip():
        return False
    domain = domain_str.strip()
    if len(domain) > 253:
        return False
    if domain.endswith("."):
        domain = domain[:-1]
    disallowed = re.compile(r"[^a-zA-Z0-9-]")
    for part in domain.split("."):
        if not part or len(part) > 63:
            return False
        if part.startswith("-") or part.endswith("-"):
            return False
        if disallowed.search(part):
            return False
    return True


def is_valid_username(username: str) -> bool:
    """Validate username (alphanumeric with hyphen/underscore/dot/at, 3-64 chars)."""
    if not isinstance(username, str):
        return False
    pattern = r"^[a-zA-Z0-9_.@-]{3,64}$"
    return bool(re.match(pattern, username.strip()))


def is_valid_cloud_name(name: str) -> bool:
    """Validate cloud instance name (alphanumeric, hyphen, underscore, 3-32 chars)."""
    if not isinstance(name, str):
        return False
    pattern = r"^[a-zA-Z0-9_-]{3,32}$"
    return bool(re.match(pattern, name.strip()))


def parse_memory_mb(mem_str: str | int) -> int:
    """Parse memory string (e.g., '1024M', '2G', '4096') into Megabytes."""
    if isinstance(mem_str, int):
        return mem_str
    if not isinstance(mem_str, str) or not mem_str.strip():
        raise ValueError(f"Invalid memory value: {mem_str}")

    clean = mem_str.strip().upper()
    if clean.isdigit():
        result = int(clean)
    elif clean.endswith("G") or clean.endswith("GB"):
        val = clean.rstrip("GB")
        result = int(float(val) * 1024)
    elif clean.endswith("M") or clean.endswith("MB"):
        val = clean.rstrip("MB")
        result = int(float(val))
    elif clean.endswith("K") or clean.endswith("KB"):
        val = clean.rstrip("KB")
        result = max(1, int(float(val) / 1024))
    else:
        raise ValueError(f"Unsupported memory unit format: {mem_str}")

    if result <= 0:
        raise ValueError(f"Memory value must be strictly positive: {mem_str}")
    return result


def is_safe_path(base_path: str | Path, target_path: str | Path) -> bool:
    """Ensure target_path does not escape base_path via directory traversal."""
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        return base == target or base in target.parents
    except Exception:
        return False
