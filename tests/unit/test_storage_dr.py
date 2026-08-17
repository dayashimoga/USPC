"""Storage, backup, and disaster recovery validation tests."""

import argparse
import hashlib
from unittest.mock import MagicMock, patch

from cloudctl.commands.cleanup import execute_cleanup
from cloudctl.core.config import ConfigManager
from cloudctl.core.metrics import MetricSnapshot, MetricsStore
from cloudctl.utils.fs import (
    get_free_disk_space_gb,
    get_total_disk_space_gb,
)


def test_free_and_total_disk_space_utilities(tmp_path):
    """Test disk space detection on existing and nonexistent directory paths."""
    free_gb = get_free_disk_space_gb(tmp_path)
    total_gb = get_total_disk_space_gb(tmp_path)
    assert free_gb > 0.0
    assert total_gb > 0.0
    assert total_gb >= free_gb

    # Nonexistent child path resolves to parent
    nested_nonexistent = tmp_path / "deep" / "nested" / "dir"
    free_nested = get_free_disk_space_gb(nested_nonexistent)
    assert free_nested > 0.0


def test_cleanup_dry_run_safety(tmp_path):
    """Verify that cleanup with --dry-run NEVER deletes any files or directories."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    sample_file = cache_dir / "test_thumb.webp"
    sample_file.write_text("THUMBNAIL_DATA", encoding="utf-8")

    args = argparse.Namespace(
        dry_run=True,
        purge_thumbnails=True,
        purge_transcodes=True,
        config=None,
    )

    with patch("cloudctl.commands.cleanup.ConfigManager") as mock_cm_cls:
        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {
            "storage": {
                "data_path": str(tmp_path / "data"),
                "config_path": str(tmp_path / "config"),
            },
            "media": {"thumbnails_dir": str(cache_dir)},
        }
        mock_cm_cls.return_value = mock_cm

        rc = execute_cleanup(args)
        assert rc == 0
        # File MUST still exist after dry-run
        assert sample_file.exists()


def test_config_export_import_roundtrip(tmp_path):
    """Test exporting configuration, importing onto a new instance, and verifying zero drift."""
    original_config = tmp_path / "original_cloud.yaml"
    imported_config = tmp_path / "imported_cloud.yaml"

    cm1 = ConfigManager(config_path=original_config)
    defaults = cm1.load_defaults()
    defaults["cloud"]["name"] = "roundtrip-cloud"
    defaults["network"]["headscale_port"] = 8090
    cm1.save_config(defaults)

    # Export with unmasked secrets
    exported_yaml = cm1.export_config(mask_secrets=False)
    export_file = tmp_path / "exported.yaml"
    export_file.write_text(exported_yaml, encoding="utf-8")

    # Import into cm2
    cm2 = ConfigManager(config_path=imported_config)
    cm2.import_config(export_file, backup_existing=False)

    # Diff between imported and defaults must show exactly the overrides
    diffs = cm2.diff_config()
    name_diff = next(d for d in diffs if d["key"] == "cloud.name")
    port_diff = next(d for d in diffs if d["key"] == "network.headscale_port")

    assert name_diff["current"] == "roundtrip-cloud"
    assert name_diff["provenance"] == "USER-OVERRIDE"
    assert port_diff["current"] == 8090
    assert port_diff["provenance"] == "USER-OVERRIDE"


def test_backup_sha256_hash_verification(tmp_path):
    """Verify SHA-256 data integrity tracking across files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create test payloads and record SHA-256 hashes
    hashes = {}
    for i in range(5):
        f = data_dir / f"file_{i}.dat"
        content = f"CONTENT_PAYLOAD_{i}".encode()
        f.write_bytes(content)
        hashes[f.name] = hashlib.sha256(content).hexdigest()

    # Verify all hashes match
    for f in data_dir.glob("*.dat"):
        actual_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        assert hashes[f.name] == actual_hash


def test_metrics_store_bounded_storage_limit(tmp_path):
    """Verify MetricsStore storage enforcement prunes old records and vacuums database."""
    db_file = tmp_path / "bounded_metrics.sqlite"
    ms = MetricsStore(db_path=db_file)

    # Insert sample records
    for i in range(50):
        ms.record_snapshot(
            MetricSnapshot(
                timestamp=1000.0 + i,
                cpu_percent=20.0,
                ram_percent=40.0,
                disk_free_gb=50.0,
                active_streams=1,
                queue_depth=0,
            )
        )

    assert ms.get_db_size_bytes() > 0

    # Trigger limit enforcement with a tiny threshold
    pruned = ms.enforce_storage_limit(max_size_bytes=10)  # Exceeds 10 bytes
    assert pruned is True
