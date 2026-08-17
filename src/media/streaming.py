"""High-performance HTTP 206 Partial Content Range streaming engine."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from cloudctl.core.logging import get_logger
from src.media.metadata import detect_media_type_and_mime

logger = get_logger("media.streaming")


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """
    Parse HTTP Range header value (e.g., 'bytes=1000-2000', 'bytes=5000-', 'bytes=-1000').
    Returns (start_byte, end_byte).
    """
    if not range_header or not range_header.startswith("bytes="):
        return 0, file_size - 1

    unit, ranges_str = range_header.split("=", 1)
    if unit.strip() != "bytes" or not ranges_str:
        return 0, file_size - 1

    # In case of multiple ranges (multipart), we handle the first range
    first_range = ranges_str.split(",")[0].strip()
    if "-" not in first_range:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Malformed Range header format",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    start_str, end_str = first_range.split("-", 1)

    # Suffix range: bytes=-500 (last 500 bytes)
    if not start_str and end_str:
        suffix_len = int(end_str)
        if suffix_len <= 0:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start = max(0, file_size - suffix_len)
        end = file_size - 1
        return start, end

    # Prefix range: bytes=500- (from 500 to end)
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1

    if start < 0 or start >= file_size or end < start:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Requested range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    # Clamp end to last byte
    end = min(end, file_size - 1)
    return start, end


async def chunk_generator(
    file_path: Path,
    start: int,
    end: int,
    chunk_size: int = 65536,
) -> AsyncGenerator[bytes, None]:
    """
    Asynchronously stream file content chunk-by-chunk within range [start, end].
    Never loads entire file into memory.
    """
    total_to_read = end - start + 1
    bytes_read = 0

    with open(file_path, "rb") as f:
        f.seek(start)
        while bytes_read < total_to_read:
            to_read = min(chunk_size, total_to_read - bytes_read)
            chunk = f.read(to_read)
            if not chunk:
                break
            bytes_read += len(chunk)
            yield chunk


def create_streaming_response(
    file_path: Path,
    request: Request,
    chunk_size_kb: int = 64,
    mime_type: str | None = None,
) -> Response:
    """
    Create an efficient HTTP 206 Partial Content or 200 OK streaming response.
    """
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range") or request.headers.get("Range")

    if not mime_type:
        _, mime_type = detect_media_type_and_mime(file_path)

    chunk_size = chunk_size_kb * 1024

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
        "Cache-Control": "public, max-age=3600",
    }

    if range_header:
        start, end = parse_range_header(range_header, file_size)
        content_length = end - start + 1
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(content_length)

        return StreamingResponse(
            chunk_generator(file_path, start, end, chunk_size),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type=mime_type,
        )
    else:
        headers["Content-Length"] = str(file_size)
        return StreamingResponse(
            chunk_generator(file_path, 0, file_size - 1, chunk_size),
            status_code=status.HTTP_200_OK,
            headers=headers,
            media_type=mime_type,
        )
