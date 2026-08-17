"""Security-hardened unit tests verifying authentication, authorization, IDOR, and rate limiting."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.media.app import create_app
from src.media.auth import (
    create_media_token,
    validate_file_access,
    verify_media_token,
)
from src.media.config import MediaConfig
from src.media.fairness import ConcurrencyManager, SlidingWindowRateLimiter


def test_token_creation_and_tampering():
    from src.media.auth import verify_media_token_user

    secret = "super_secret_jwt_key_test"
    item_id = "test_item_123"
    user_id = "user_alice"

    token = create_media_token(item_id, secret, user_id=user_id, expires_in_seconds=60)
    assert token.startswith("user_alice:")

    # Valid token verification with user extraction
    valid, extracted_user = verify_media_token_user(item_id, token, secret)
    assert valid is True
    assert extracted_user == "user_alice"
    assert verify_media_token(item_id, token, secret) is True

    # IDOR attempt: using token generated for item_123 to access item_456
    idor_valid, _ = verify_media_token_user("different_item_456", token, secret)
    assert idor_valid is False
    assert verify_media_token("different_item_456", token, secret) is False

    # Tampered signature
    parts = token.split(":")
    tampered_token = f"{parts[0]}:{parts[1]}:deadbeefdeadbeef"
    tampered_valid, _ = verify_media_token_user(item_id, tampered_token, secret)
    assert tampered_valid is False

    # Expired token
    expired_token = create_media_token(item_id, secret, user_id=user_id, expires_in_seconds=-10)
    expired_valid, _ = verify_media_token_user(item_id, expired_token, secret)
    assert expired_valid is False

    # Malformed token strings
    assert verify_media_token_user(item_id, "invalid_no_colon", secret) == (False, "")
    assert verify_media_token_user(item_id, "", secret) == (False, "")


def test_path_traversal_prevention(temp_dir: Path):
    base_storage = temp_dir / "safe_storage"
    base_storage.mkdir()

    safe_file = base_storage / "photo.jpg"
    safe_file.write_text("image_data", encoding="utf-8")

    # Safe file within base
    assert validate_file_access(base_storage, safe_file) == safe_file.resolve()

    # Traversal attempt: ../../../outside.txt
    outside_file = temp_dir / "sensitive.txt"
    outside_file.write_text("secret_root_data", encoding="utf-8")

    traversal_path = base_storage / ".." / "sensitive.txt"
    with pytest.raises(HTTPException) as exc:
        validate_file_access(base_storage, traversal_path)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rate_limiter_enforcement():
    limiter = SlidingWindowRateLimiter(max_requests_per_minute=3)
    client_ip = "192.168.1.100"

    # 3 allowed requests
    await limiter.check_rate_limit(client_ip)
    await limiter.check_rate_limit(client_ip)
    await limiter.check_rate_limit(client_ip)

    # 4th request must be rejected with 429
    with pytest.raises(HTTPException) as exc:
        await limiter.check_rate_limit(client_ip)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_concurrency_manager_limits():
    mgr = ConcurrencyManager(max_global_streams=2, max_streams_per_user=1)

    # User 1 acquires stream 1
    await mgr.acquire_stream_slot("user1", "s1")
    assert mgr.get_total_active_streams() == 1

    # User 1 tries to acquire 2nd stream (exceeds per-user limit)
    with pytest.raises(HTTPException) as exc:
        await mgr.acquire_stream_slot("user1", "s2")
    assert exc.value.status_code == 429

    # User 2 acquires stream 2 (global limit reaches 2)
    await mgr.acquire_stream_slot("user2", "s3")
    assert mgr.get_total_active_streams() == 2

    # User 3 tries to acquire stream (exceeds global capacity)
    with pytest.raises(HTTPException) as exc:
        await mgr.acquire_stream_slot("user3", "s4")
    assert exc.value.status_code == 429

    # Release stream
    await mgr.release_stream_slot("user1", "s1")
    assert mgr.get_total_active_streams() == 1

    # Release remaining
    await mgr.release_stream_slot("user2", "s3")
    assert mgr.get_total_active_streams() == 0


def test_api_authenticated_stream_and_upload(temp_dir: Path):
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True)
    cache_dir = temp_dir / "cache"

    secret = "jwt_secret_test_12345"
    cfg = MediaConfig(
        data_path=data_dir, cache_path=cache_dir, jwt_secret=secret, max_upload_size_mb=1
    )
    app = create_app(cfg)

    # Write a test media file
    vid = data_dir / "sample.mp4"
    vid.write_bytes(b"VIDEO_CONTENT_BYTES_" * 500)

    with TestClient(app) as client:
        # 1. Unauthenticated stream request must return 401
        res_unauth = client.get("/api/media/sample_id/stream")
        assert res_unauth.status_code == 401

        # 2. Trigger scan with valid Bearer auth
        res_scan = client.post("/api/scan", headers={"Authorization": f"Bearer {secret}"})
        assert res_scan.status_code == 200

        # Get item list
        res_list = client.get("/api/media")
        assert res_list.status_code == 200
        items = res_list.json()["items"]
        assert len(items) >= 1
        item_id = items[0]["id"]

        # 3. Request authenticated token
        res_detail = client.get(f"/api/media/{item_id}")
        assert res_detail.status_code == 200
        token = res_detail.json()["playback_token"]

        # 4. Stream media with valid token query parameter
        res_stream = client.get(f"/api/media/{item_id}/stream?token={token}")
        assert res_stream.status_code in (200, 206)

        # 5. Stream media with invalid / forged token -> 401
        res_bad_stream = client.get(f"/api/media/{item_id}/stream?token=invalid_token_xyz")
        assert res_bad_stream.status_code == 401

        # 6. Upload file with valid Bearer token
        upload_content = b"TEST_UPLOADED_IMAGE_CONTENT"
        res_upload = client.post(
            "/api/upload",
            headers={"Authorization": f"Bearer {secret}"},
            files={"file": ("uploaded_pic.png", upload_content, "image/png")},
        )
        assert res_upload.status_code == 200
        assert res_upload.json()["status"] == "uploaded"

        # 7. Upload with malicious path traversal in filename -> sanitized safely
        res_bad_upload = client.post(
            "/api/upload",
            headers={"Authorization": f"Bearer {secret}"},
            files={"file": (".hidden_evil.sh", b"evil", "text/plain")},
        )
        assert res_bad_upload.status_code == 400
