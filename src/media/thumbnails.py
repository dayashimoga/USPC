"""Thumbnail and poster generation for photos, video frames, and audio cover art."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import ensure_directory
from cloudctl.utils.shell import run_command

logger = get_logger("media.thumbnails")


class ThumbnailGenerator:
    """Generates high-performance cached thumbnails and preview images."""

    def __init__(self, thumbnails_dir: Path, default_width: int = 320):
        self.thumbnails_dir = Path(thumbnails_dir).expanduser().resolve()
        self.default_width = default_width
        self.ffmpeg_path = shutil.which("ffmpeg")
        ensure_directory(self.thumbnails_dir, mode=0o750)

    def get_thumbnail_path(self, item_id: str) -> Path:
        """Get destination path for a generated thumbnail."""
        return self.thumbnails_dir / f"{item_id}.webp"

    def generate(
        self, file_path: Path, item_id: str, media_type: str, duration: float | None = None
    ) -> Path | None:
        """Generate thumbnail based on media type."""
        dest = self.get_thumbnail_path(item_id)
        if dest.exists():
            return dest

        try:
            if media_type == "image":
                return self._generate_image_thumbnail(file_path, dest)
            elif media_type == "video":
                return self._generate_video_thumbnail(file_path, dest, duration)
            elif media_type == "audio":
                return self._generate_audio_thumbnail(file_path, dest)
            else:
                return self._generate_fallback_badge(file_path.stem, dest, "FILE", (100, 116, 139))
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail for {file_path}: {e}")
            return self._generate_fallback_badge(
                file_path.stem, dest, media_type.upper(), (71, 85, 105)
            )

    def _generate_image_thumbnail(self, src: Path, dest: Path) -> Path:
        """Resize image preserving aspect ratio and save as optimized WebP."""
        with Image.open(src) as img:
            # Handle orientation
            try:
                from PIL import ImageOps

                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            img.thumbnail((self.default_width, self.default_width), Image.Resampling.LANCZOS)
            img.save(dest, "WEBP", quality=85)
        return dest

    def _generate_video_thumbnail(
        self, src: Path, dest: Path, duration: float | None = None
    ) -> Path:
        """Capture video frame at 10% duration via FFmpeg, or create video poster badge."""
        if self.ffmpeg_path:
            seek_time = max(1.0, (duration or 10.0) * 0.1)
            temp_jpg = dest.with_suffix(".tmp.jpg")
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss",
                str(seek_time),
                "-i",
                str(src),
                "-vframes",
                "1",
                "-vf",
                f"scale={self.default_width}:-1",
                "-q:v",
                "3",
                str(temp_jpg),
            ]
            res = run_command(cmd, timeout=20.0)
            if res.success and temp_jpg.exists():
                with Image.open(temp_jpg) as img:
                    img.save(dest, "WEBP", quality=85)
                temp_jpg.unlink(missing_ok=True)
                return dest

        # Fallback video badge
        return self._generate_fallback_badge(src.stem, dest, "VIDEO", (37, 99, 235))

    def _generate_audio_thumbnail(self, src: Path, dest: Path) -> Path:
        """Extract embedded album art via FFmpeg or create stylish audio badge."""
        if self.ffmpeg_path:
            temp_jpg = dest.with_suffix(".tmp.jpg")
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(src),
                "-an",
                "-vcodec",
                "copy",
                str(temp_jpg),
            ]
            res = run_command(cmd, timeout=10.0)
            if res.success and temp_jpg.exists():
                with Image.open(temp_jpg) as img:
                    img.thumbnail(
                        (self.default_width, self.default_width), Image.Resampling.LANCZOS
                    )
                    img.save(dest, "WEBP", quality=85)
                temp_jpg.unlink(missing_ok=True)
                return dest

        # Fallback audio badge
        return self._generate_fallback_badge(src.stem, dest, "AUDIO", (147, 51, 234))

    def _generate_fallback_badge(
        self, title: str, dest: Path, badge_type: str, color_rgb: tuple[int, int, int]
    ) -> Path:
        """Generate high-contrast, modern graphic badge placeholder thumbnail."""
        size = (self.default_width, int(self.default_width * 0.75))
        img = Image.new("RGB", size, color=(15, 23, 42))  # Slate dark background
        draw = ImageDraw.Draw(img)

        # Draw accent banner
        draw.rectangle([0, 0, size[0], 8], fill=color_rgb)

        # Draw icon/badge type
        draw.text((20, 30), f"[{badge_type}]", fill=color_rgb)

        # Draw truncated title text
        display_title = title[:30] + "..." if len(title) > 30 else title
        draw.text((20, 70), display_title, fill=(226, 232, 240))

        img.save(dest, "WEBP", quality=80)
        return dest
