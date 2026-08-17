"""Metadata extraction for video, audio, and image files."""

from __future__ import annotations

import json
import mimetypes
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from cloudctl.core.logging import get_logger
from cloudctl.utils.shell import run_command

logger = get_logger("media.metadata")

# Ensure common MIME types are registered
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("video/quicktime", ".mov")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/flac", ".flac")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("audio/aac", ".aac")
mimetypes.add_type("audio/mp4", ".m4a")
mimetypes.add_type("image/webp", ".webp")


@dataclass
class ExtractedMetadata:
    """Extracted technical and descriptive metadata."""

    mime_type: str
    media_type: str  # video, audio, image
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    codec: str | None = None


def detect_media_type_and_mime(file_path: Path) -> tuple[str, str]:
    """Determine media category (video/audio/image) and standard MIME type."""
    ext = file_path.suffix.lower().lstrip(".")
    mime, _ = mimetypes.guess_type(str(file_path))
    if not mime:
        if ext in ("mp4", "m4v", "mov", "mkv", "webm", "avi", "wmv", "flv"):
            mime = "video/" + ("mp4" if ext in ("mp4", "m4v") else ext)
        elif ext in ("mp3", "aac", "m4a", "flac", "ogg", "opus", "wav", "wma"):
            mime = "audio/" + ("mpeg" if ext == "mp3" else ext)
        elif ext in ("jpg", "jpeg", "png", "webp", "gif", "bmp", "svg", "tiff"):
            mime = "image/" + ("jpeg" if ext in ("jpg", "jpeg") else ext)
        else:
            mime = "application/octet-stream"

    if mime.startswith("video/"):
        media_type = "video"
    elif mime.startswith("audio/"):
        media_type = "audio"
    elif mime.startswith("image/"):
        media_type = "image"
    else:
        media_type = "unknown"

    return media_type, mime


class MetadataExtractor:
    """Extracts technical parameters and tags from media files."""

    def __init__(self):
        self.ffprobe_path = shutil.which("ffprobe")

    def extract(self, file_path: Path) -> ExtractedMetadata:
        """Extract metadata from media file."""
        media_type, mime = detect_media_type_and_mime(file_path)

        if media_type == "image":
            return self._extract_image_metadata(file_path, mime)
        elif self.ffprobe_path:
            return self._extract_ffprobe_metadata(file_path, media_type, mime)
        else:
            return self._extract_fallback_metadata(file_path, media_type, mime)

    def _extract_image_metadata(self, file_path: Path, mime: str) -> ExtractedMetadata:
        """Extract image dimensions and format using Pillow."""
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                return ExtractedMetadata(
                    mime_type=mime,
                    media_type="image",
                    width=w,
                    height=h,
                    title=file_path.stem,
                )
        except Exception as e:
            logger.debug(f"Failed image inspection on {file_path}: {e}")
            return ExtractedMetadata(mime_type=mime, media_type="image", title=file_path.stem)

    def _extract_ffprobe_metadata(
        self, file_path: Path, media_type: str, mime: str
    ) -> ExtractedMetadata:
        """Extract rich video/audio streams and format tags using FFprobe."""
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return self._extract_fallback_metadata(file_path, media_type, mime)

        try:
            data = json.loads(res.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])

            duration = float(fmt.get("duration", 0)) if fmt.get("duration") else None
            tags = fmt.get("tags", {})
            title = tags.get("title") or tags.get("TITLE") or file_path.stem
            artist = tags.get("artist") or tags.get("ARTIST")
            album = tags.get("album") or tags.get("ALBUM")

            width = None
            height = None
            codec = None

            for st in streams:
                if st.get("codec_type") == "video" and not width:
                    width = int(st.get("width", 0)) or None
                    height = int(st.get("height", 0)) or None
                    codec = st.get("codec_name")
                elif st.get("codec_type") == "audio" and not codec:
                    codec = st.get("codec_name")

            return ExtractedMetadata(
                mime_type=mime,
                media_type=media_type,
                duration_seconds=duration,
                width=width,
                height=height,
                title=title,
                artist=artist,
                album=album,
                codec=codec,
            )
        except Exception as e:
            logger.warning(f"Error parsing ffprobe output for {file_path}: {e}")
            return self._extract_fallback_metadata(file_path, media_type, mime)

    def _extract_fallback_metadata(
        self, file_path: Path, media_type: str, mime: str
    ) -> ExtractedMetadata:
        """Lightweight fallback when ffprobe is not installed."""
        return ExtractedMetadata(
            mime_type=mime,
            media_type=media_type,
            title=file_path.stem,
        )
