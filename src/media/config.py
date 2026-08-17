"""Configuration for USPC Media Service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MediaConfig:
    """Media microservice settings."""

    data_path: Path = field(
        default_factory=lambda: (
            Path(os.environ.get("USPC_DATA_PATH", "~/.uspc/data/nextcloud")).expanduser().resolve()
        )
    )
    cache_path: Path = field(
        default_factory=lambda: (
            Path(os.environ.get("USPC_CACHE_PATH", "~/.uspc/data/media_cache"))
            .expanduser()
            .resolve()
        )
    )
    jwt_secret: str = field(
        default_factory=lambda: os.environ.get(
            "USPC_JWT_SECRET", "default-insecure-dev-secret-replace-in-prod"
        )
    )
    host: str = field(default_factory=lambda: os.environ.get("USPC_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("USPC_PORT", "8085")))
    thumbnail_width: int = 320
    preview_width: int = 800
    chunk_size_kb: int = 64
    max_transcode_jobs: int = 2
    background_processing: bool = True
    max_upload_size_mb: int = 4096
    allowed_origins: list[str] = field(
        default_factory=lambda: os.environ.get("USPC_ALLOWED_ORIGINS", "*").split(",")
    )

    video_extensions: set[str] = field(
        default_factory=lambda: {"mp4", "webm", "mov", "mkv", "avi", "wmv", "flv", "m4v", "ts"}
    )
    audio_extensions: set[str] = field(
        default_factory=lambda: {"mp3", "aac", "m4a", "flac", "ogg", "opus", "wav", "wma", "aiff"}
    )
    image_extensions: set[str] = field(
        default_factory=lambda: {"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg", "tiff", "ico"}
    )

    @property
    def db_path(self) -> Path:
        return self.cache_path / "media_index.sqlite"

    @property
    def thumbnails_dir(self) -> Path:
        return self.cache_path / "thumbnails"

    @property
    def transcoded_dir(self) -> Path:
        return self.cache_path / "transcoded"

    @property
    def is_insecure_secret(self) -> bool:
        return self.jwt_secret == "default-insecure-dev-secret-replace-in-prod"
