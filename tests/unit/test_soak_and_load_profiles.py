"""Unit tests for sustained soak endurance testing, load profiles, and DR RPO/RTO metrics."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from cloudctl.commands.benchmark import execute_benchmark
from cloudctl.core.backup import BackupManager
from cloudctl.core.performance import (
    LOAD_PROFILES,
    SoakTestResult,
    run_soak_test,
)


def test_load_profiles_structure():
    assert "SMOKE" in LOAD_PROFILES
    assert "NORMAL" in LOAD_PROFILES
    assert "HEAVY" in LOAD_PROFILES
    assert "MEDIA_HEAVY" in LOAD_PROFILES
    assert "MULTI_USER" in LOAD_PROFILES
    assert "STRESS" in LOAD_PROFILES
    assert "SOAK" in LOAD_PROFILES

    for _name, prof in LOAD_PROFILES.items():
        assert "concurrency" in prof
        assert "ops_per_client" in prof
        assert "description" in prof
        assert prof["concurrency"] >= 1


def test_run_soak_test_execution(temp_dir: Path):
    result = run_soak_test(temp_dir / "soak_test", duration_seconds=1.0, concurrency=2)
    assert isinstance(result, SoakTestResult)
    assert result.duration_seconds >= 0.5
    assert result.total_cycles > 0
    assert result.success_count == result.total_cycles
    assert result.error_count == 0
    assert result.throughput_ops_sec > 0.0
    assert result.stability_verdict in ("STABLE", "DEGRADED")


def test_backup_rpo_and_rto_calculations(temp_dir: Path, mock_config_dict: dict):
    bm = BackupManager(mock_config_dict)

    # Calculate RPO with no snapshots
    with patch.object(bm, "list_snapshots", return_value=[]):
        rpo = bm.calculate_rpo_hours()
        assert rpo == 24.0

    # Calculate RPO with existing snapshots
    mock_snap = MagicMock(id="abc123", time="2026-08-17 12:00:00")
    with patch.object(bm, "list_snapshots", return_value=[mock_snap]):
        rpo_recent = bm.calculate_rpo_hours()
        assert rpo_recent <= 1.0

    # Measure RTO
    rto = bm.measure_rto_seconds(dataset_size_gb=10.0)
    assert rto >= 5.0


def test_execute_benchmark_with_soak_and_load_profile(temp_dir: Path, mock_config_dict: dict):
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    args = argparse.Namespace(
        config=str(cfg_file),
        profile=None,
        stress=False,
        soak=True,
        duration=0.5,
        load_profile="smoke",
        json=False,
    )
    rc = execute_benchmark(args)
    assert rc == 0

    # JSON mode
    args_json = argparse.Namespace(
        config=str(cfg_file),
        profile=None,
        stress=False,
        soak=True,
        duration=0.5,
        load_profile="normal",
        json=True,
    )
    rc_json = execute_benchmark(args_json)
    assert rc_json == 0
