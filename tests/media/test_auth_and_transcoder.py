"""Unit tests for media auth tokens, path traversal security, and transcoder."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from src.media.auth import (
    create_media_token,
    validate_file_access,
    verify_media_token,
)
from src.media.transcoder import Transcoder


def test_media_tokens():
    secret = "my-ultra-secret-test-key-321"
    item_id = "video_item_123"

    # Generate valid token
    token = create_media_token(item_id, secret, expires_in_seconds=3600)
    assert verify_media_token(item_id, token, secret) is True

    # Reject wrong item ID
    assert verify_media_token("different_item", token, secret) is False

    # Reject tampered token
    tampered = token[:-4] + "ffff"
    assert verify_media_token(item_id, tampered, secret) is False

    # Expired token
    expired_token = create_media_token(item_id, secret, expires_in_seconds=-10)
    assert verify_media_token(item_id, expired_token, secret) is False


def test_path_traversal_validation(temp_dir: Path):
    base_dir = temp_dir / "data"
    base_dir.mkdir()

    safe_file = base_dir / "folder" / "photo.jpg"
    safe_file.parent.mkdir()
    safe_file.write_text("ok")

    assert validate_file_access(base_dir, safe_file) == safe_file.resolve()

    # Traversal attempt
    escape_file = temp_dir / "etc" / "passwd"
    escape_file.parent.mkdir()
    escape_file.write_text("secret")

    with pytest.raises(HTTPException) as exc:
        validate_file_access(base_dir, escape_file)
    assert exc.value.status_code == 403


def test_transcoder_helpers(temp_dir: Path):
    cache = temp_dir / "cache"
    tc = Transcoder(cache_dir=cache)

    assert tc.is_browser_native(Path("video.mp4")) is True
    assert tc.is_browser_native(Path("song.mp3")) is True
    assert tc.is_browser_native(Path("movie.mkv")) is False
    assert tc.is_browser_native(Path("clip.avi")) is False
