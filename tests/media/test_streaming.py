"""Unit tests for HTTP 206 Range streaming engine."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.media.streaming import (
    chunk_generator,
    create_streaming_response,
    parse_range_header,
)


def test_parse_range_header():
    total_size = 10000

    # Explicit range: bytes=0-499 (500 bytes)
    start, end = parse_range_header("bytes=0-499", total_size)
    assert (start, end) == (0, 499)

    # Prefix range: bytes=5000-
    start, end = parse_range_header("bytes=5000-", total_size)
    assert (start, end) == (5000, 9999)

    # Suffix range: bytes=-1000 (last 1000 bytes)
    start, end = parse_range_header("bytes=-1000", total_size)
    assert (start, end) == (9000, 9999)

    # Empty or missing range
    start, end = parse_range_header("", total_size)
    assert (start, end) == (0, 9999)

    # Invalid range bounds -> 416
    with pytest.raises(HTTPException) as exc:
        parse_range_header("bytes=15000-20000", total_size)
    assert exc.value.status_code == 416

    with pytest.raises(HTTPException) as exc:
        parse_range_header("bytes=500-200", total_size)
    assert exc.value.status_code == 416


@pytest.mark.asyncio
async def test_chunk_generator(temp_dir: Path):
    f = temp_dir / "stream_data.bin"
    content = b"0123456789" * 1000  # 10,000 bytes
    f.write_bytes(content)

    # Read slice [100, 299] (200 bytes) with 64-byte chunks
    chunks = []
    async for chunk in chunk_generator(f, start=100, end=299, chunk_size=64):
        chunks.append(chunk)

    combined = b"".join(chunks)
    assert len(combined) == 200
    assert combined == content[100:300]


def test_streaming_response_headers(temp_dir: Path):
    f = temp_dir / "video_sample.mp4"
    content = b"VIDEO_HEADER_DATA_" * 500  # 9000 bytes
    f.write_bytes(content)

    # Helper mock request
    scope = {"type": "http", "headers": [(b"range", b"bytes=100-599")]}
    req = Request(scope)

    resp = create_streaming_response(f, req, chunk_size_kb=64, mime_type="video/mp4")
    assert resp.status_code == 206
    assert resp.headers["Content-Range"] == f"bytes 100-599/{len(content)}"
    assert resp.headers["Content-Length"] == "500"
    assert resp.headers["Accept-Ranges"] == "bytes"

    # Full request (No Range header)
    scope_full = {"type": "http", "headers": []}
    req_full = Request(scope_full)

    resp_full = create_streaming_response(f, req_full, chunk_size_kb=64, mime_type="video/mp4")
    assert resp_full.status_code == 200
    assert resp_full.headers["Content-Length"] == str(len(content))
