"""Cryptographic utilities for key and token generation."""

from __future__ import annotations

import base64
import hashlib
import secrets
import string
from pathlib import Path


def generate_secure_password(length: int = 32) -> str:
    """Generate a high-entropy password containing alphanumeric and special characters."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    # Ensure at least one uppercase, lowercase, digit, and symbol
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*()-_=+" for c in password)
        ):
            return password


def generate_hex_token(length_bytes: int = 32) -> str:
    """Generate cryptographically secure hexadecimal token."""
    return secrets.token_hex(length_bytes)


def generate_base64_key(length_bytes: int = 32) -> str:
    """Generate cryptographically secure base64 string (WireGuard / symmetric key)."""
    random_bytes = secrets.token_bytes(length_bytes)
    return base64.b64encode(random_bytes).decode("utf-8")


def calculate_file_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file efficiently without reading entire file into RAM."""
    p = Path(file_path).expanduser().resolve()
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_data_sha256(data: bytes | str) -> str:
    """Calculate SHA-256 hash of in-memory data."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()
