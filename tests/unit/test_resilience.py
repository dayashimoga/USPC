"""Failure injection and resilience tests simulating infrastructure, database, container, and resource faults."""

from unittest.mock import MagicMock, patch

import pytest

from cloudctl.core.backup import BackupManager
from cloudctl.core.config import ConfigManager
from cloudctl.core.health import HealthChecker
from cloudctl.core.metrics import MetricsStore
from cloudctl.core.security import SecurityChecker
from src.media.fairness import should_throttle_background_jobs


def test_postgres_connection_failure():
    """Simulate PostgreSQL connection failure and verify degraded health reporting."""
    config = {
        "services": {
            "postgres": {"port": 5432, "db_name": "nextcloud", "user": "nextcloud"},
            "redis": {"port": 6379},
            "nextcloud": {"port": 8081},
        },
        "media": {"enabled": True, "port": 8085},
        "network": {"headscale_port": 8080},
    }
    hc = HealthChecker(config)

    with patch("cloudctl.core.container.ContainerManager.get_container_status") as mock_stat:
        mock_stat.return_value = MagicMock(status="stopped", image="postgres:16")
        report = hc.run_all_checks()
        pg_check = next(c for c in report.checks if "postgres" in c.name)
        assert pg_check.status == "DEGRADED"
        assert report.overall_status in ("DEGRADED", "UNHEALTHY")


def test_redis_cache_failure():
    """Simulate Redis failure and ensure platform detects degradation."""
    config = {
        "services": {
            "postgres": {"port": 5432},
            "redis": {"port": 6379},
            "nextcloud": {"port": 8081},
        },
        "media": {"enabled": True, "port": 8085},
        "network": {"headscale_port": 8080},
    }
    hc = HealthChecker(config)

    def _side_effect(name):
        if "redis" in name:
            return MagicMock(status="missing", image="redis:7.2")
        return MagicMock(status="running", image="test:latest")

    with patch(
        "cloudctl.core.container.ContainerManager.get_container_status", side_effect=_side_effect
    ):
        report = hc.run_all_checks()
        redis_check = next(c for c in report.checks if "redis" in c.name)
        assert redis_check.status == "UNHEALTHY"


def test_disk_full_backup_protection(tmp_path):
    """Simulate zero free disk space and verify backup/storage fails gracefully."""
    config = {
        "backup": {"enabled": True, "target_path": str(tmp_path / "backups")},
        "storage": {
            "data_path": str(tmp_path / "data"),
            "config_path": str(tmp_path / "config"),
            "min_free_space_gb": 10.0,
        },
    }
    bm = BackupManager(config)

    with patch("cloudctl.utils.fs.get_free_disk_space_gb", return_value=0.0):
        with patch("cloudctl.core.backup.run_command") as mock_run:
            mock_run.return_value = MagicMock(
                success=False, stderr="Fatal: No space left on device"
            )
            res = bm.create_backup()
            assert res is False


import yaml


def test_corrupted_yaml_configuration(tmp_path):
    """Verify corrupted YAML raises clear parsing error."""
    bad_config_file = tmp_path / "corrupted_cloud.yaml"
    bad_config_file.write_text("cloud: { name: [broken yaml: invalid", encoding="utf-8")

    cm = ConfigManager(config_path=bad_config_file)
    with pytest.raises((yaml.YAMLError, ValueError)):
        cm.load_config()


def test_corrupted_sqlite_metrics_store(tmp_path):
    """Verify MetricsStore handles corrupted SQLite file without crashing."""
    corrupted_db = tmp_path / "metrics_corrupted.sqlite"
    corrupted_db.write_text("NOT_A_VALID_SQLITE_HEADER_GARBAGE_DATA", encoding="utf-8")

    ms = MetricsStore(db_path=corrupted_db)
    summary = ms.get_historical_summary()
    assert summary["sample_count"] == 0


def test_high_cpu_ram_load_shedding():
    """Verify background task throttle responds to CPU > 85% or RAM > 90%."""
    with patch("psutil.cpu_percent", return_value=92.0):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(percent=50.0)
            assert should_throttle_background_jobs() is True

    with patch("psutil.cpu_percent", return_value=30.0):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(percent=95.0)
            assert should_throttle_background_jobs() is True

    with patch("psutil.cpu_percent", return_value=25.0):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(percent=45.0)
            assert should_throttle_background_jobs() is False


def test_network_socket_probe_timeout(tmp_path):
    """Verify SecurityChecker handles socket timeouts during port scans."""
    config = {"network": {"mode": "private"}}
    sc = SecurityChecker(config, repo_root=tmp_path)

    with patch("socket.socket") as mock_sock:
        mock_instance = MagicMock()
        mock_instance.connect_ex.side_effect = TimeoutError("Socket timeout")
        mock_sock.return_value = mock_instance

        res = sc.check_exposed_ports()
        assert res.status == "PASS"
