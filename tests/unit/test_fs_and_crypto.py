"""Unit tests for filesystem, shell, and crypto utilities."""

from pathlib import Path

import pytest

from cloudctl.utils.crypto import (
    calculate_data_sha256,
    calculate_file_sha256,
    generate_base64_key,
    generate_hex_token,
    generate_secure_password,
)
from cloudctl.utils.fs import (
    atomic_write,
    ensure_directory,
    get_free_disk_space_gb,
    get_total_disk_space_gb,
    remove_path_safely,
)
from cloudctl.utils.shell import mask_secrets, run_command


def test_fs_operations(temp_dir: Path):
    sub = temp_dir / "a" / "b" / "c"
    created = ensure_directory(sub)
    assert created.exists()
    assert created.is_dir()

    # Atomic write text & binary
    txt_file = sub / "test.txt"
    atomic_write(txt_file, "hello atomic world")
    assert txt_file.read_text(encoding="utf-8") == "hello atomic world"

    bin_file = sub / "test.bin"
    atomic_write(bin_file, b"\x00\x01\x02\x03")
    assert bin_file.read_bytes() == b"\x00\x01\x02\x03"

    # Disk space
    free_gb = get_free_disk_space_gb(temp_dir)
    total_gb = get_total_disk_space_gb(temp_dir)
    assert free_gb > 0
    assert total_gb >= free_gb

    # Removal
    assert remove_path_safely(txt_file) is True
    assert txt_file.exists() is False
    assert remove_path_safely(temp_dir / "non_existing") is False
    assert remove_path_safely(sub) is True


def test_crypto_helpers(temp_dir: Path):
    pw = generate_secure_password(32)
    assert len(pw) == 32
    assert any(c.isupper() for c in pw)
    assert any(c.islower() for c in pw)
    assert any(c.isdigit() for c in pw)

    token = generate_hex_token(16)
    assert len(token) == 32  # 16 bytes = 32 hex chars

    b64_key = generate_base64_key(32)
    assert len(b64_key) > 0

    data_hash = calculate_data_sha256("test_data")
    assert len(data_hash) == 64

    # File hash
    f = temp_dir / "hash_test.txt"
    f.write_text("test_data", encoding="utf-8")
    assert calculate_file_sha256(f) == data_hash


def test_shell_runner_and_masking():
    res = run_command(["python", "-c", "print('hello from shell')"])
    assert res.success is True
    assert "hello from shell" in res.stdout
    assert res.returncode == 0

    # Test secret masking
    secret = "SUPER_SECRET_TOKEN_999"
    masked = mask_secrets(f"command output with {secret} exposed", [secret])
    assert secret not in masked
    assert "********" in masked

    # Error checking
    res_err = run_command(["python", "-c", "import sys; sys.exit(42)"])
    assert res_err.success is False
    assert res_err.returncode == 42

    with pytest.raises(RuntimeError):
        run_command(["python", "-c", "import sys; sys.exit(1)"], check=True)
