"""Complete coverage tests to ensure >90% code coverage across all modules."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cloudctl.cli import main
from cloudctl.core.container import ContainerManager
from src.media.metadata import MetadataExtractor
from src.media.thumbnails import ThumbnailGenerator
from src.media.transcoder import Transcoder


def test_cli_all_subcommand_dispatches(temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    from cloudctl.core.config import ConfigManager

    ConfigManager(config_path=cfg_file).save_config(
        {
            "version": "0.1.0",
            "cloud": {
                "name": "mycloud",
                "environment": "production",
                "domain": "mycloud.local",
                "admin_user": "admin",
                "admin_email": "admin@mycloud.local",
            },
            "runtime": {"engine": "docker", "rootless": True, "vm_memory_mb": 2048, "vm_cpus": 1},
            "storage": {
                "data_path": str(temp_dir / "d"),
                "config_path": str(temp_dir / "cfg"),
                "min_free_space_gb": 0.1,
                "external_mounts": [],
            },
            "network": {
                "mode": "private",
                "vpn_subnet": "100.64.0.0/10",
                "headscale_port": 8080,
                "public_http_port": 80,
                "public_https_port": 443,
                "enable_magic_dns": True,
            },
            "services": {
                "nextcloud": {"version": "27.1.4-apache", "port": 8081},
                "postgres": {"version": "16.1-alpine", "port": 5432, "db_name": "db", "user": "u"},
                "redis": {"version": "7.2-alpine", "port": 6379},
            },
            "media": {
                "enabled": True,
                "port": 8085,
                "thumbnail_width": 320,
                "preview_width": 800,
                "max_transcode_jobs": 2,
                "chunk_size_kb": 64,
                "background_processing": False,
                "index_on_upload": True,
                "supported_video": ["mp4"],
                "supported_audio": ["mp3"],
                "supported_image": ["jpg"],
            },
            "backup": {
                "enabled": True,
                "target_type": "local",
                "target_path": str(temp_dir / "b"),
                "retention_days": 10,
                "schedule": "0 2 * * *",
                "verify_after_backup": True,
            },
            "security": {
                "enforce_mfa": False,
                "auto_security_updates": True,
                "firewall_enabled": True,
                "tls_enabled": False,
            },
            "performance": {
                "profile": "standard",
                "max_concurrent_streams": 10,
                "max_streams_per_user": 3,
                "max_transcode_concurrency": 2,
                "rate_limit_requests_per_minute": 600,
                "db_connection_pool_size": 20,
            },
        }
    )

    with (
        patch("cloudctl.core.container.ContainerManager.start_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.stop_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.restart_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.remove_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.get_logs", return_value="fake log"),
        patch("cloudctl.core.backup.BackupManager.create_backup", return_value=True),
        patch("cloudctl.core.backup.BackupManager.restore_backup", return_value=True),
        patch(
            "cloudctl.core.migration.MigrationManager.export_bundle",
            return_value=temp_dir / "m.tar.gz",
        ),
        patch("cloudctl.core.migration.MigrationManager.import_bundle", return_value=True),
        patch(
            "cloudctl.commands.test_cmd.run_command",
            return_value=MagicMock(returncode=0, stdout="test ok", stderr=""),
        ),
        patch("cloudctl.utils.shell.run_command") as mock_shell,
    ):
        mock_shell.return_value = MagicMock(returncode=0, stdout="test ok", stderr="")

        assert main(["-c", str(cfg_file), "init", "--force"]) == 0
        assert main(["-c", str(cfg_file), "start"]) == 0
        assert main(["-c", str(cfg_file), "stop"]) == 0
        assert main(["-c", str(cfg_file), "restart"]) == 0
        assert main(["-c", str(cfg_file), "status"]) in (0, 1)
        assert main(["-c", str(cfg_file), "doctor"]) in (0, 1)
        assert main(["-c", str(cfg_file), "performance"]) == 0
        assert main(["-c", str(cfg_file), "benchmark"]) == 0
        assert main(["-c", str(cfg_file), "cleanup", "--dry-run"]) == 0
        assert main(["-c", str(cfg_file), "update", "--dry-run"]) == 0
        assert main(["-c", str(cfg_file), "backup"]) == 0
        assert main(["-c", str(cfg_file), "restore", "--dry-run"]) == 0
        assert (
            main(["-c", str(cfg_file), "migrate", "export", "-o", str(temp_dir / "exp.tar.gz")])
            == 0
        )
        assert (
            main(["-c", str(cfg_file), "migrate", "import", "-i", str(temp_dir / "exp.tar.gz")])
            == 0
        )
        assert main(["-c", str(cfg_file), "logs", "-s", "media"]) == 0
        assert main(["-c", str(cfg_file), "security-check"]) in (0, 1)
        assert main(["-c", str(cfg_file), "test", "--media-only"]) == 0
        assert main(["bundle", "create", "-o", str(temp_dir / "bundle.tar.gz")]) == 0
        assert main(["-c", str(cfg_file), "config", "validate"]) == 0
        assert main(["-c", str(cfg_file), "config", "diff"]) == 0
        assert main(["-c", str(cfg_file), "config", "export"]) == 0
        assert main(["-c", str(cfg_file), "readiness"]) in (0, 1)
        assert main(["-c", str(cfg_file), "uninstall", "--force"]) == 0


def test_metadata_extractor_ffprobe_mocked(temp_dir: Path):
    extractor = MetadataExtractor()
    extractor.ffprobe_path = "ffprobe"
    sample_file = temp_dir / "vid.mp4"
    sample_file.write_bytes(b"dummy")

    fake_json = '{"format": {"duration": "120.0", "tags": {"title": "T", "artist": "A", "album": "Al"}}, "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}]}'

    with patch("src.media.metadata.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout=fake_json)
        meta = extractor._extract_ffprobe_metadata(sample_file, "video", "video/mp4")
        assert meta.duration_seconds == 120.0
        assert meta.width == 1280
        assert meta.codec == "h264"


def test_thumbnails_ffmpeg_mocked(temp_dir: Path):
    thumbs_dir = temp_dir / "t"
    gen = ThumbnailGenerator(thumbs_dir, default_width=320)
    gen.ffmpeg_path = "ffmpeg"
    src_vid = temp_dir / "src.mp4"
    src_vid.write_bytes(b"data")

    dest_webp = thumbs_dir / "item1.webp"

    with (
        patch("src.media.thumbnails.run_command") as mock_run,
        patch("PIL.Image.open") as mock_open,
    ):
        mock_run.return_value = MagicMock(success=True)
        mock_img_inst = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_img_inst

        temp_jpg = dest_webp.with_suffix(".tmp.jpg")
        temp_jpg.write_bytes(b"jpg")
        res_vid = gen._generate_video_thumbnail(src_vid, dest_webp, 10.0)
        assert res_vid == dest_webp

        res_aud = gen._generate_audio_thumbnail(src_vid, dest_webp)
        assert res_aud == dest_webp


@pytest.mark.asyncio
async def test_transcoder_async_flow(temp_dir: Path):
    cache = temp_dir / "transcode_cache"
    tc = Transcoder(cache, max_concurrency=1)
    tc.ffmpeg_path = "ffmpeg"

    src_mkv = temp_dir / "video.mkv"
    src_mkv.write_bytes(b"mkv_data")

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        dest = tc.transcode_dir / "item_x.mp4"
        dest.with_suffix(".tmp.mp4").write_bytes(b"mp4_data")

        res = await tc.transcode_to_mp4(src_mkv, "item_x")
        assert res is not None
        assert res.name == "item_x.mp4"


def test_container_podman_pod_creation():
    cm = ContainerManager(engine="podman")
    cm.engine = "podman"
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True)
        assert cm.create_pod([(8080, 8080)]) is True
