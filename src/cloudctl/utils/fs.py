"""Filesystem helper utilities for USPC."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def ensure_directory(path: str | Path, mode: int = 0o750) -> Path:
    """Create directory with parent directories if missing and enforce permissions where supported."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(p, mode)
        except OSError:
            pass
    return p


def atomic_write(target_path: str | Path, content: str | bytes, mode: int = 0o600) -> Path:
    """Atomically write file content using a temporary file and atomic replace."""
    dest = Path(target_path).expanduser().resolve()
    ensure_directory(dest.parent)

    is_binary = isinstance(content, bytes)
    temp_dir = dest.parent

    with tempfile.NamedTemporaryFile(
        mode="wb" if is_binary else "w",
        dir=temp_dir,
        delete=False,
        encoding=None if is_binary else "utf-8",
    ) as tf:
        tf.write(content)
        temp_name = tf.name

    temp_path = Path(temp_name)
    if os.name != "nt":
        try:
            os.chmod(temp_path, mode)
        except OSError:
            pass

    temp_path.replace(dest)
    return dest


def get_free_disk_space_gb(path: str | Path) -> float:
    """Return free disk space at given path in Gigabytes."""
    p = Path(path).expanduser().resolve()
    # Find existing parent if path doesn't exist yet
    while not p.exists() and p.parent != p:
        p = p.parent
    if not p.exists():
        p = Path.cwd()

    usage = shutil.disk_usage(p)
    return usage.free / (1024**3)


def get_total_disk_space_gb(path: str | Path) -> float:
    """Return total disk space at given path in Gigabytes."""
    p = Path(path).expanduser().resolve()
    while not p.exists() and p.parent != p:
        p = p.parent
    if not p.exists():
        p = Path.cwd()

    usage = shutil.disk_usage(p)
    return usage.total / (1024**3)


def remove_path_safely(path: str | Path) -> bool:
    """Safely remove a file or directory tree."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return False
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p, ignore_errors=True)
    else:
        try:
            p.unlink()
        except OSError:
            return False
    return True
