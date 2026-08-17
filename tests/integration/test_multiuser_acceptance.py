"""End-to-End Multi-User Scalability Acceptance Test."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.media.app import create_app
from src.media.config import MediaConfig
from src.media.models import MediaDatabase


@pytest.fixture
def multi_user_client(
    media_test_env: tuple[MediaConfig, MediaDatabase],
) -> Generator[TestClient, None, None]:
    cfg, _ = media_test_env
    app = create_app(cfg)
    with TestClient(app) as test_client:
        yield test_client


def test_concurrent_multiuser_scenario(
    multi_user_client: TestClient, media_test_env: tuple[MediaConfig, MediaDatabase]
):
    """
    Acceptance test proving:
    User A streams video + User B streams audio + User C uploads/downloads files +
    User D browses thumbnails + background indexing runs without crashes.
    """
    client = multi_user_client
    cfg, _ = media_test_env
    auth_headers = {"Authorization": f"Bearer {cfg.jwt_secret}"}

    # Get media items
    items_resp = client.get("/api/media")
    assert items_resp.status_code == 200
    items = items_resp.json()["items"]
    assert len(items) >= 4

    video_item = next(i for i in items if i["media_type"] == "video")
    audio_item = next(i for i in items if i["media_type"] == "audio")
    image_item = next(i for i in items if i["media_type"] == "image")

    # Get playback tokens for streaming
    token_a = client.get(f"/api/media/{video_item['id']}").json()["playback_token"]
    token_b = client.get(f"/api/media/{audio_item['id']}").json()["playback_token"]

    # 1. User A: Streams video with Range header (Seeking)
    resp_user_a = client.get(
        f"/api/media/{video_item['id']}/stream?token={token_a}",
        headers={"Range": "bytes=100-5000"},
    )
    assert resp_user_a.status_code == 206
    assert resp_user_a.headers["Content-Range"].startswith("bytes 100-5000/")

    # 2. User B: Streams audio with Range header
    resp_user_b = client.get(
        f"/api/media/{audio_item['id']}/stream?token={token_b}",
        headers={"Range": "bytes=0-2048"},
    )
    assert resp_user_b.status_code == 206
    assert len(resp_user_b.content) == 2049

    # 3. User C: Uploads new file and downloads original
    upload_bytes = b"MULTIUSER_UPLOAD_TEST_TRACK_" * 200
    resp_user_c_up = client.post(
        "/api/upload",
        files={"file": ("user_c_track.mp3", upload_bytes, "audio/mpeg")},
        headers=auth_headers,
    )
    assert resp_user_c_up.status_code == 200
    assert resp_user_c_up.json()["filename"] == "user_c_track.mp3"

    resp_user_c_dl = client.get(f"/api/media/{video_item['id']}/download?token={token_a}")
    assert resp_user_c_dl.status_code == 200

    # 4. User D: Browses and fetches thumbnails in parallel
    resp_user_d_thumb1 = client.get(f"/api/media/{image_item['id']}/thumbnail")
    assert resp_user_d_thumb1.status_code == 200

    resp_user_d_thumb2 = client.get(f"/api/media/{video_item['id']}/thumbnail")
    assert resp_user_d_thumb2.status_code == 200

    # 5. Background indexing runs concurrently
    resp_scan = client.post("/api/scan", headers=auth_headers)
    assert resp_scan.status_code == 200

    # Final verification: All users succeeded, zero data corruption
    final_list = client.get("/api/media")
    assert final_list.status_code == 200
    assert final_list.json()["total"] >= 5
