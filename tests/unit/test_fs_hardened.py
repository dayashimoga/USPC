"""Comprehensive tests for filesystem utilities ensuring >95% branch coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cloudctl.utils.fs import (
    atomic_write,
    ensure_directory,
    get_free_disk_space_gb,
    get_total_disk_space_gb,
    remove_path_safely,
)


def test_ensure_directory(temp_dir: Path):
    target = temp_dir / "sub" / "deep_dir"
    d = ensure_directory(target)
    assert d.exists()
    assert d.is_dir()


def test_atomic_write_text_and_binary(temp_dir: Path):
    # Text write
    f_txt = temp_dir / "test.txt"
    atomic_write(f_txt, "hello world text")
    assert f_txt.read_text(encoding="utf-8") == "hello world text"

    # Binary write
    f_bin = temp_dir / "test.bin"
    atomic_write(f_bin, b"\x00\x01\x02\x03\x04")
    assert f_bin.read_bytes() == b"\x00\x01\x02\x03\x04"

    # Overwrite existing
    atomic_write(f_txt, "overwritten text")
    assert f_txt.read_text(encoding="utf-8") == "overwritten text"


def test_disk_space_utilities(temp_dir: Path):
    # Existing path
    free_gb = get_free_disk_space_gb(temp_dir)
    assert free_gb > 0.0

    total_gb = get_total_disk_space_gb(temp_dir)
    assert total_gb > 0.0

    # Non-existent deep path
    non_existent = temp_dir / "does" / "not" / "exist"
    assert get_free_disk_space_gb(non_existent) > 0.0
    assert get_total_disk_space_gb(non_existent) > 0.0

    # Path where parent is itself (root) or cwd fallback
    with patch(
        "shutil.disk_usage",
        return_value=MagicMock(free=10 * 1024**3, total=100 * 1024**3, used=90 * 1024**3),
    ):
        assert get_free_disk_space_gb("Z:\\completely\\fake\\virtual\\path") == 10.0
        assert get_total_disk_space_gb("Z:\\completely\\fake\\virtual\\path") == 100.0


def test_remove_path_safely_all_branches(temp_dir: Path):
    # Non-existent path returns False
    assert not remove_path_safely(temp_dir / "non_existent_file.xyz")

    # Regular file
    f = temp_dir / "sample.txt"
    f.write_text("data", encoding="utf-8")
    assert remove_path_safely(f)
    assert not f.exists()

    # Directory tree
    d = temp_dir / "tree"
    (d / "nested").mkdir(parents=True)
    (d / "nested" / "file.txt").write_text("data", encoding="utf-8")
    assert remove_path_safely(d)
    assert not d.exists()

    # File unlink OSError
    f2 = temp_dir / "unlink_err.txt"
    f2.write_text("data", encoding="utf-8")
    with patch.object(Path, "unlink", side_effect=OSError("Locked")):
        assert not remove_path_safely(f2)
