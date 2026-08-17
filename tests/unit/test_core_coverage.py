"""Targeted unit tests for deep code coverage across core and media systems."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudctl.commands.install import execute_install
from cloudctl.core.backup import BackupManager
from cloudctl.core.container import ContainerManager, ContainerStatus
from cloudctl.core.health import HealthChecker
from cloudctl.core.logging import setup_logger
from cloudctl.core.reporting import print_security_report, print_status_dashboard
from cloudctl.core.security import SecurityCheckResult
from src.media.config import MediaConfig
from src.media.models import MediaDatabase
from src.media.thumbnails import ThumbnailGenerator
from src.media.transcoder import Transcoder
from src.media.worker import BackgroundWorker


def test_container_manager_methods():
    cm = ContainerManager()

    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(
            success=True,
            stdout='[{"Id": "123456789012", "State": {"Status": "running", "Health": {"Status": "healthy"}}, "Config": {"Image": "alpine:latest"}}]',
            stderr="",
            returncode=0,
        )
        assert cm.create_pod() is True
        assert cm.run_container("test-container", "alpine:latest") is True
        assert cm.stop_container("test-container") is True
        assert cm.start_container("test-container") is True
        assert cm.restart_container("test-container") is True
        assert cm.remove_container("test-container") is True
        assert cm.inspect_container("test-container") is not None
        assert cm.get_logs("test-container") is not None
        assert cm.exec_command("test-container", ["echo", "hi"]).success is True
        status = cm.get_container_status("test-container")
        assert status.status == "running"
        assert status.health == "healthy"


def test_health_and_reporting(mock_config_dict: dict, temp_dir: Path):
    checker = HealthChecker(mock_config_dict)
    real_stat = ContainerStatus(
        name="uspc-nextcloud",
        id="123456",
        image="nextcloud:27",
        status="running",
        health="healthy",
        ports=["8081"],
        created_at="2026-08-17",
    )
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=True),
        patch(
            "cloudctl.core.container.ContainerManager.get_container_status", return_value=real_stat
        ),
    ):
        report = checker.run_all_checks()
        assert report.overall_status in ("HEALTHY", "DEGRADED", "UNHEALTHY")

    # Print dashboard (console & json)
    print_status_dashboard(report, mock_config_dict, json_output=False)
    print_status_dashboard(report, mock_config_dict, json_output=True)

    # Security reporting
    sec_results = [
        SecurityCheckResult(name="Test Check 1", status="PASS", details="All good"),
        SecurityCheckResult(
            name="Test Check 2", status="WARN", details="Minor warn", remediation="Fix it"
        ),
    ]
    res_pass = print_security_report(sec_results, strict=False)
    assert res_pass == 0
    res_fail = print_security_report(sec_results, strict=True)
    assert res_fail == 1


def test_backup_manager_extended(mock_config_dict: dict, temp_dir: Path):
    bm = BackupManager(mock_config_dict, secrets_dir=temp_dir / "secrets")

    with (
        patch("cloudctl.core.backup.run_command") as mock_run,
        patch("cloudctl.core.container.ContainerManager.exec_command") as mock_exec,
    ):
        mock_run.return_value = MagicMock(
            success=True, stdout="snapshot1\nsnapshot2", stderr="", returncode=0
        )
        mock_exec.return_value = MagicMock(success=True, stdout="-- DB DUMP SQL")
        assert bm.init_repository() is True
        assert bm.create_backup(tag="test", verify_after=True) is True
        assert bm.verify_repository() is True
        assert len(bm.list_snapshots()) == 2
        assert bm.restore_backup(snapshot_id="snapshot1", target_dir=temp_dir / "restored") is True
        assert bm.test_restore_isolation() is True


def test_install_full_flow(mock_config_dict: dict, temp_dir: Path):
    import argparse

    cfg_file = temp_dir / "cloud.yaml"
    from cloudctl.core.config import ConfigManager

    ConfigManager(config_path=cfg_file).save_config(mock_config_dict)

    args = argparse.Namespace(config=str(cfg_file), dry_run=False, skip_smoke_test=True)
    with (
        patch("cloudctl.core.container.ContainerManager.create_pod", return_value=True),
        patch("cloudctl.core.container.ContainerManager.run_container", return_value=True),
        patch("cloudctl.core.storage.StorageManager.initialize_storage") as mock_init,
    ):
        mock_init.return_value = MagicMock(
            base_data=temp_dir / "data",
            base_config=temp_dir / "config",
            postgres_data=temp_dir / "data" / "pg",
            redis_data=temp_dir / "data" / "redis",
            nextcloud_data=temp_dir / "data" / "nc",
            nextcloud_config=temp_dir / "config" / "nc",
            media_cache=temp_dir / "cache",
            headscale_config=temp_dir / "config" / "hs",
            headscale_data=temp_dir / "data" / "hs",
        )
        assert execute_install(args) == 0


def test_thumbnail_video_and_audio_badge(temp_dir: Path):
    thumbs_dir = temp_dir / "thumbnails"
    gen = ThumbnailGenerator(thumbnails_dir=thumbs_dir, default_width=320)
    badge = gen._generate_fallback_badge(
        "My Title", thumbs_dir / "badge.webp", "VIDEO", (37, 99, 235)
    )
    assert badge.exists()


@pytest.mark.asyncio
async def test_worker_and_transcoder_lifecycle(temp_dir: Path):
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "test.mp4").write_bytes(b"data")

    cfg = MediaConfig(
        data_path=data_dir, cache_path=temp_dir / "cache", background_processing=False
    )
    db = MediaDatabase(cfg.db_path)

    worker = BackgroundWorker(cfg, db, interval_seconds=1)
    await worker.start()
    worker.trigger_scan()
    await asyncio.sleep(0.1)
    await worker.stop()

    # Transcoder
    tc = Transcoder(cache_dir=temp_dir / "cache", max_concurrency=1)
    assert tc.is_browser_native(Path("sample.mp4")) is True
    res_tc = await tc.transcode_to_mp4(Path("non_existing.mkv"), "item_999")
    assert res_tc is None


def test_logging_setup_safe(temp_dir: Path):
    log_f = temp_dir / "test_safe.log"
    logger = setup_logger(level="DEBUG", log_file=log_f, json_format=True)
    logger.info("JSON log payload")
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)
