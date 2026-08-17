"""Integration tests for FastAPI Media microservice endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.media.app import create_app
from src.media.config import MediaConfig
from src.media.models import MediaDatabase


@pytest.fixture
def client(media_test_env: tuple[MediaConfig, MediaDatabase]) -> Generator[TestClient, None, None]:
    cfg, _ = media_test_env
    app = create_app(cfg)
    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "stats" in data
    assert data["stats"]["total"] >= 4


def test_api_media_listing(client: TestClient):
    # Full list
    resp = client.get("/api/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    assert len(data["items"]) >= 4

    # Filter by video
    v_resp = client.get("/api/media?type=video")
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert all(i["media_type"] == "video" for i in v_data["items"])

    # Search filter
    s_resp = client.get("/api/media?search=photo")
    assert s_resp.status_code == 200
    s_data = s_resp.json()
    assert len(s_data["items"]) >= 1


def test_api_item_details_and_streaming(client: TestClient):
    list_resp = client.get("/api/media?type=video")
    items = list_resp.json()["items"]
    assert len(items) > 0
    vid_id = items[0]["id"]

    # 1. Get Details
    det_resp = client.get(f"/api/media/{vid_id}")
    assert det_resp.status_code == 200
    details = det_resp.json()
    assert "playback_token" in details
    assert "stream_url" in details
    token = details["playback_token"]

    # 2. Get Thumbnail
    thumb_resp = client.get(f"/api/media/{vid_id}/thumbnail")
    assert thumb_resp.status_code == 200
    assert "image/" in thumb_resp.headers["content-type"]

    # 3. HTTP 206 Range Stream using playback token
    stream_resp = client.get(
        f"/api/media/{vid_id}/stream?token={token}",
        headers={"Range": "bytes=0-1023"},
    )
    assert stream_resp.status_code == 206
    assert stream_resp.headers["Accept-Ranges"] == "bytes"
    assert stream_resp.headers["Content-Length"] == "1024"
    assert "bytes 0-1023/" in stream_resp.headers["Content-Range"]
    assert len(stream_resp.content) == 1024

    # 4. Direct Download using playback token
    dl_resp = client.get(f"/api/media/{vid_id}/download?token={token}")
    assert dl_resp.status_code == 200
    assert "attachment;" in dl_resp.headers["content-disposition"]


def test_api_upload_and_scan(client: TestClient, media_test_env: tuple[MediaConfig, MediaDatabase]):
    cfg, _ = media_test_env
    auth_headers = {"Authorization": f"Bearer {cfg.jwt_secret}"}

    # Test Upload
    dummy_audio_bytes = b"ID3_TAG_HEADER_TEST_AUDIO_UPLOAD_" * 100
    files = {"file": ("uploaded_track.mp3", dummy_audio_bytes, "audio/mpeg")}

    up_resp = client.post("/api/upload", files=files, headers=auth_headers)
    assert up_resp.status_code == 200
    up_data = up_resp.json()
    assert up_data["status"] == "uploaded"
    assert up_data["filename"] == "uploaded_track.mp3"

    # Trigger scan
    scan_resp = client.post("/api/scan", headers=auth_headers)
    assert scan_resp.status_code == 200
    assert scan_resp.json()["status"] == "scan_triggered"
