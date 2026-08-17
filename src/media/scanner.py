"""Filesystem scanner for detecting new, updated, and deleted media."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cloudctl.core.logging import get_logger
from cloudctl.utils.crypto import calculate_data_sha256
from cloudctl.utils.validators import is_safe_path
from src.media.config import MediaConfig

logger = get_logger("media.scanner")


@dataclass
class ScannedFile:
    """Discovered media file on disk."""

    id: str
    abs_path: Path
    rel_path: str
    filename: str
    size_bytes: int
    mtime: float
    extension: str


class StorageScanner:
    """Walks the storage tree to discover media assets."""

    def __init__(self, config: MediaConfig):
        self.config = config
        self.supported_exts = (
            config.video_extensions | config.audio_extensions | config.image_extensions
        )

    def scan(self) -> list[ScannedFile]:
        """Recursively scan data directory for media files safely."""
        data_dir = self.config.data_path.resolve()
        results: list[ScannedFile] = []

        if not data_dir.exists():
            logger.debug(f"Data directory does not exist yet: {data_dir}")
            return results

        for root, dirs, files in os.walk(data_dir, followlinks=False):
            # Skip hidden folders and cache directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ("media_cache", "thumbnails", "appdata_")
            ]

            for file in files:
                if file.startswith("."):
                    continue

                ext = file.rsplit(".", 1)[-1].lower() if "." in file else ""
                if ext in self.supported_exts:
                    abs_p = Path(root) / file
                    try:
                        # Ensure real path does not escape data directory (symlink attack protection)
                        if not is_safe_path(data_dir, abs_p):
                            logger.warning(f"Skipping symlink/escape path: {abs_p}")
                            continue

                        stat = abs_p.stat()
                        rel_p = str(abs_p.relative_to(data_dir)).replace("\\", "/")
                        item_id = calculate_data_sha256(rel_p)[:16]

                        results.append(
                            ScannedFile(
                                id=item_id,
                                abs_path=abs_p,
                                rel_path=rel_p,
                                filename=file,
                                size_bytes=stat.st_size,
                                mtime=stat.st_mtime,
                                extension=ext,
                            )
                        )
                    except (OSError, ValueError) as e:
                        logger.debug(f"Skipping inaccessible file {abs_p}: {e}")

        logger.debug(f"Scanner discovered {len(results)} media file(s) in {data_dir}")
        return results
