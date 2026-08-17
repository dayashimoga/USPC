"""Shared pytest fixtures and test data generators."""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image

# Ensure src/ is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from src.media.config import MediaConfig
from src.media.models import MediaDatabase


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide an isolated temporary directory for test operations."""
    with tempfile.TemporaryDirectory(prefix="uspc_test_") as td:
        yield Path(td)


@pytest.fixture
def mock_config_dict(temp_dir: Path) -> dict:
    """Provide a validated sample configuration dictionary pointing to temp dirs."""
    return {
        "version": "0.1.0",
        "cloud": {
            "name": "testcloud",
            "environment": "testing",
            "domain": "testcloud.local",
            "admin_user": "testadmin",
            "admin_email": "admin@testcloud.local",
        },
        "runtime": {
            "engine": "docker",
            "rootless": True,
            "vm_memory_mb": 2048,
            "vm_cpus": 2,
        },
        "storage": {
            "data_path": str(temp_dir / "data"),
            "config_path": str(temp_dir / "config"),
            "min_free_space_gb": 1.0,
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
            "nextcloud": {
                "version": "27.1.4-apache",
                "port": 8081,
                "memory_limit": "512M",
                "upload_max_filesize": "1G",
            },
            "postgres": {
                "version": "16.1-alpine",
                "port": 5432,
                "db_name": "nextcloud",
                "user": "nextcloud",
            },
            "redis": {
                "version": "7.2-alpine",
                "port": 6379,
            },
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
            "supported_video": ["mp4", "webm", "mov", "mkv"],
            "supported_audio": ["mp3", "aac", "m4a", "flac", "wav"],
            "supported_image": ["jpg", "jpeg", "png", "webp", "gif"],
        },
        "backup": {
            "enabled": True,
            "target_type": "local",
            "target_path": str(temp_dir / "backups"),
            "retention_days": 14,
            "schedule": "0 2 * * *",
            "verify_after_backup": True,
        },
        "security": {
            "enforce_mfa": False,
            "auto_security_updates": True,
            "firewall_enabled": True,
            "tls_enabled": False,
        },
    }


@pytest.fixture
def sample_media_files(temp_dir: Path) -> dict[str, Path]:
    """Create genuine small test media files (photo, video bytes, audio bytes)."""
    data_dir = temp_dir / "data" / "nextcloud"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Real valid JPEG Image
    img_path = data_dir / "test_photo.jpg"
    img = Image.new("RGB", (640, 480), color=(40, 120, 200))
    img.save(img_path, "JPEG")

    # 2. Valid PNG Image
    png_path = data_dir / "test_image.png"
    png_img = Image.new("RGBA", (300, 300), color=(100, 200, 50, 255))
    png_img.save(png_path, "PNG")

    # 3. Video file fixture (binary chunked bytes)
    vid_path = data_dir / "test_video.mp4"
    # Create valid synthetic byte stream for chunk/range testing
    vid_data = b"USPC_SYNTHETIC_MP4_CONTAINER_STREAM_TEST_PAYLOAD_" * 5000  # ~250 KB
    vid_path.write_bytes(vid_data)

    # 4. Audio file fixture
    aud_path = data_dir / "test_song.mp3"
    aud_data = b"USPC_SYNTHETIC_MP3_AUDIO_STREAM_TEST_PAYLOAD_" * 3000  # ~135 KB
    aud_path.write_bytes(aud_data)

    return {
        "image": img_path,
        "png": png_path,
        "video": vid_path,
        "audio": aud_path,
        "data_dir": data_dir,
    }


@pytest.fixture
def media_test_env(
    temp_dir: Path, sample_media_files: dict[str, Path]
) -> tuple[MediaConfig, MediaDatabase]:
    """Provide an initialized MediaConfig and MediaDatabase for testing."""
    cfg = MediaConfig(
        data_path=sample_media_files["data_dir"],
        cache_path=temp_dir / "cache",
        jwt_secret="test-secret-key-12345",
        background_processing=False,
    )
    db = MediaDatabase(cfg.db_path)
    return cfg, db
