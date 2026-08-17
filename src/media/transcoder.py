"""Optional background transcoding queue for browser-incompatible video formats."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import ensure_directory

logger = get_logger("media.transcoder")


class Transcoder:
    """Manages asynchronous transcoding jobs for non-native containers (e.g. MKV, AVI -> MP4 H.264/AAC)."""

    def __init__(self, cache_dir: Path, max_concurrency: int = 2):
        self.transcode_dir = Path(cache_dir) / "transcoded"
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.ffmpeg_path = shutil.which("ffmpeg")
        ensure_directory(self.transcode_dir, mode=0o750)

    def is_browser_native(self, file_path: Path) -> bool:
        """Check if format is natively supported by modern browsers without transcoding."""
        ext = file_path.suffix.lower().lstrip(".")
        return ext in (
            "mp4",
            "webm",
            "mp3",
            "aac",
            "m4a",
            "ogg",
            "opus",
            "wav",
            "jpg",
            "jpeg",
            "png",
            "webp",
            "gif",
        )

    async def transcode_to_mp4(self, src_path: Path, item_id: str) -> Path | None:
        """Transcode video to web-optimized faststart MP4 (H.264 + AAC) asynchronously."""
        if not self.ffmpeg_path:
            logger.debug(f"FFmpeg not installed; skipping transcode for {src_path.name}")
            return None

        dest_path = self.transcode_dir / f"{item_id}.mp4"
        if dest_path.exists():
            return dest_path

        temp_dest = dest_path.with_suffix(".tmp.mp4")

        async with self.semaphore:
            logger.info(f"Starting background transcode: {src_path.name} -> {dest_path.name}")
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(src_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(temp_dest),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0 and temp_dest.exists():
                temp_dest.replace(dest_path)
                logger.info(f"Transcode complete: {dest_path.name}")
                return dest_path
            else:
                logger.warning(
                    f"Transcoding failed for {src_path.name}: {stderr.decode(errors='replace')[:200]}"
                )
                temp_dest.unlink(missing_ok=True)
                return None
