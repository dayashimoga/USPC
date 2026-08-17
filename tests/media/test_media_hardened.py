"""Media streaming, indexing, and range seeking edge-case tests."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.media.config import MediaConfig
from src.media.metadata import MetadataExtractor
from src.media.scanner import StorageScanner
from src.media.streaming import create_streaming_response, parse_range_header


def test_parse_range_header_edge_cases():
    file_size = 10000

    # 1. Normal byte range
    start, end = parse_range_header("bytes=0-499", file_size)
    assert (start, end) == (0, 499)

    # 2. Open-ended range (prefix)
    start, end = parse_range_header("bytes=5000-", file_size)
    assert (start, end) == (5000, 9999)

    # 3. Suffix range (last N bytes)
    start, end = parse_range_header("bytes=-500", file_size)
    assert (start, end) == (9500, 9999)

    # 4. Multiple ranges (uses first range)
    start, end = parse_range_header("bytes=100-200,300-400", file_size)
    assert (start, end) == (100, 200)

    # 5. Invalid / Unsatisfiable ranges (HTTP 416)
    with pytest.raises(HTTPException) as exc_1:
        parse_range_header("bytes=15000-20000", file_size)
    assert exc_1.value.status_code == 416

    with pytest.raises(HTTPException) as exc_2:
        parse_range_header("bytes=500-100", file_size)  # end < start
    assert exc_2.value.status_code == 416

    with pytest.raises(HTTPException) as exc_3:
        parse_range_header("bytes=-0", file_size)
    assert exc_3.value.status_code == 416

    with pytest.raises(HTTPException) as exc_4:
        parse_range_header("bytes=malformed", file_size)
    assert exc_4.value.status_code == 416


def test_streaming_response_headers_and_status(tmp_path):
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"A" * 5000)

    # Request with Range header -> HTTP 206
    req_range = MagicMock()
    req_range.headers = {"Range": "bytes=1000-1999"}
    resp_206 = create_streaming_response(video_file, req_range, chunk_size_kb=1)

    assert resp_206.status_code == 206
    assert resp_206.headers["Accept-Ranges"] == "bytes"
    assert resp_206.headers["Content-Range"] == "bytes 1000-1999/5000"
    assert resp_206.headers["Content-Length"] == "1000"
    assert "video/mp4" in resp_206.headers["Content-Type"]

    # Request without Range header -> HTTP 200
    req_full = MagicMock()
    req_full.headers = {}
    resp_200 = create_streaming_response(video_file, req_full, chunk_size_kb=1)

    assert resp_200.status_code == 200
    assert resp_200.headers["Accept-Ranges"] == "bytes"
    assert resp_200.headers["Content-Length"] == "5000"


def test_scanner_ignores_unsupported_extensions(tmp_path):
    media_dir = tmp_path / "media_store"
    media_dir.mkdir()

    # Create valid and unsupported files
    (media_dir / "movie.mp4").write_text("mp4", encoding="utf-8")
    (media_dir / "song.mp3").write_text("mp3", encoding="utf-8")
    (media_dir / "photo.jpg").write_text("jpg", encoding="utf-8")
    (media_dir / "doc.pdf").write_text("pdf", encoding="utf-8")
    (media_dir / "script.sh").write_text("sh", encoding="utf-8")
    (media_dir / "archive.zip").write_text("zip", encoding="utf-8")

    cfg = MediaConfig(data_path=media_dir)
    scanner = StorageScanner(config=cfg)
    found = scanner.scan()
    rel_names = {f.filename for f in found}

    assert "movie.mp4" in rel_names
    assert "song.mp3" in rel_names
    assert "photo.jpg" in rel_names
    assert "doc.pdf" not in rel_names
    assert "script.sh" not in rel_names
    assert "archive.zip" not in rel_names


def test_metadata_extraction_fallback_on_corrupted_file(tmp_path):
    corrupt_video = tmp_path / "corrupt.mp4"
    corrupt_video.write_bytes(b"CORRUPT_NOT_A_REAL_MP4_FILE_HEADER")

    extractor = MetadataExtractor()
    meta = extractor.extract(corrupt_video)
    assert meta.title == "corrupt"
    assert meta.media_type == "video"
    assert "video" in meta.mime_type
