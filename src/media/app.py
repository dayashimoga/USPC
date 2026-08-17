"""FastAPI Application for USPC Media Service and Web UI."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cloudctl.core.logging import get_logger, setup_logger
from cloudctl.utils.fs import ensure_directory
from src.media.auth import authenticate_request, create_media_token, validate_file_access
from src.media.config import MediaConfig
from src.media.fairness import ConcurrencyManager, InFlightDeduplicator, SlidingWindowRateLimiter
from src.media.indexer import MediaIndexer
from src.media.models import MediaDatabase
from src.media.streaming import create_streaming_response
from src.media.worker import BackgroundWorker

logger = get_logger("media.api")


def create_app(config: MediaConfig | None = None) -> FastAPI:
    """Application factory for USPC Media Service."""
    if config is None:
        config = MediaConfig()

    ensure_directory(config.cache_path)
    ensure_directory(config.thumbnails_dir)
    ensure_directory(config.data_path)

    db = MediaDatabase(config.db_path)
    indexer = MediaIndexer(config, db)
    worker = BackgroundWorker(config, db)
    concurrency_mgr = ConcurrencyManager(max_global_streams=20, max_streams_per_user=4)
    rate_limiter = SlidingWindowRateLimiter(max_requests_per_minute=600)
    deduplicator = InFlightDeduplicator()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info(f"USPC Media microservice starting on port {config.port}...")
        # Initial indexing pass
        indexer.sync_all()
        if config.background_processing:
            await worker.start()
        yield
        # Shutdown
        if config.background_processing:
            await worker.stop()
        logger.info("USPC Media microservice shut down cleanly.")

    app = FastAPI(
        title="USPC Media Library & Streaming Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.config = config
    app.state.db = db
    app.state.indexer = indexer
    app.state.worker = worker
    app.state.concurrency = concurrency_mgr
    app.state.rate_limiter = rate_limiter
    app.state.deduplicator = deduplicator

    # Configure CORS
    origins = config.allowed_origins if config.allowed_origins != ["*"] else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Apply rate limiting to API routes
        if request.url.path.startswith("/api/"):
            client_ip = request.client.host if request.client else "127.0.0.1"
            await rate_limiter.check_rate_limit(client_ip)
        return await call_next(request)

    # --------------------------------------------------------------------------
    # API Routes
    # --------------------------------------------------------------------------

    @app.get("/api/health")
    async def get_health():
        """Service health and library statistics."""
        _, total_items = db.list_items(limit=1)
        _, video_count = db.list_items(media_type="video", limit=1)
        _, audio_count = db.list_items(media_type="audio", limit=1)
        _, image_count = db.list_items(media_type="image", limit=1)

        return {
            "status": "healthy",
            "version": "0.1.0",
            "active_streams": concurrency_mgr.get_total_active_streams(),
            "stats": {
                "total": total_items,
                "videos": video_count,
                "audio": audio_count,
                "images": image_count,
            },
        }

    @app.get("/api/media")
    async def list_media(
        type: str | None = Query(None, description="Filter by type: video, audio, image"),
        search: str | None = Query(None, description="Search query string"),
        sort: str = Query(
            "mtime", description="Sort by: mtime, filename, size_bytes, duration_seconds"
        ),
        order: str = Query("DESC", description="Sort direction: ASC, DESC"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        """List and search media items with pagination and sorting."""
        items, total = db.list_items(
            media_type=type,
            search=search,
            sort_by=sort,
            order=order,
            limit=limit,
            offset=offset,
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [item.to_dict() for item in items],
        }

    @app.get("/api/media/{id}")
    async def get_media_details(id: str):
        """Get item metadata and authenticated playback token."""
        item = db.get_by_id(id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
            )

        token = create_media_token(item.id, config.jwt_secret)
        data = item.to_dict()
        data["playback_token"] = token
        data["stream_url"] = f"/api/media/{item.id}/stream?token={token}"
        data["thumbnail_url"] = f"/api/media/{item.id}/thumbnail"
        data["download_url"] = f"/api/media/{item.id}/download?token={token}"
        return data

    @app.get("/api/media/{id}/thumbnail")
    async def get_media_thumbnail(id: str, request: Request):
        """Serve cached thumbnail image with HTTP caching support."""
        item = db.get_by_id(id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        thumb_file = Path(item.thumbnail_path) if item.thumbnail_path else None
        if not thumb_file or not thumb_file.exists():
            # Regenerate on demand
            abs_file = config.data_path / item.rel_path
            if abs_file.exists():
                thumb_file = indexer.thumbnail_gen.generate(
                    abs_file, item.id, item.media_type, item.duration_seconds
                )

        if not thumb_file or not thumb_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail could not be generated"
            )

        return FileResponse(
            thumb_file,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/api/media/{id}/stream")
    async def stream_media(
        id: str,
        request: Request,
        _auth: bool = Depends(authenticate_request),
    ):
        """Stream media with HTTP 206 Partial Content range requests and concurrency slots."""
        item = db.get_by_id(id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
            )

        user_id = getattr(request.state, "user_id", "default_user")
        abs_path = validate_file_access(config.data_path, config.data_path / item.rel_path)
        stream_id = f"{id}_{user_id}_{time.time()}"

        # Acquire concurrency stream slot
        await concurrency_mgr.acquire_stream_slot(user_id, stream_id)

        try:
            resp = create_streaming_response(
                file_path=abs_path,
                request=request,
                chunk_size_kb=config.chunk_size_kb,
                mime_type=item.mime_type,
            )
            return resp
        finally:
            await concurrency_mgr.release_stream_slot(user_id, stream_id)

    @app.get("/api/media/{id}/download")
    async def download_media(
        id: str,
        _auth: bool = Depends(authenticate_request),
    ):
        """Download original media file directly."""
        item = db.get_by_id(id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
            )

        abs_path = validate_file_access(config.data_path, config.data_path / item.rel_path)
        return FileResponse(
            abs_path,
            filename=item.filename,
            media_type=item.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{item.filename}"'},
        )

    @app.post("/api/scan")
    async def trigger_scan(request: Request, _auth: bool = Depends(authenticate_request)):
        """Trigger immediate background sync of filesystem."""
        user_id = getattr(request.state, "user_id", "admin")
        worker.trigger_scan()
        return {"status": "scan_triggered", "triggered_by": user_id}

    @app.post("/api/upload")
    async def upload_media(
        request: Request,
        file: UploadFile = File(...),
        _auth: bool = Depends(authenticate_request),
    ):
        """Upload media file directly into library and index immediately."""
        user_id = getattr(request.state, "user_id", "admin")
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing filename")

        # Sanitize filename (prevent path traversal like ../../evil.sh)
        clean_filename = Path(file.filename).name
        if not clean_filename or clean_filename.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid filename")

        dest_path = config.data_path / clean_filename
        validate_file_access(config.data_path, dest_path)

        # Write uploaded file with size limit enforcement
        max_bytes = config.max_upload_size_mb * 1024 * 1024
        written_bytes = 0

        with open(dest_path, "wb") as f:
            while chunk := await file.read(65536):
                written_bytes += len(chunk)
                if written_bytes > max_bytes:
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Upload exceeds maximum permitted size of {config.max_upload_size_mb} MB",
                    )
                f.write(chunk)

        # Trigger immediate sync
        stats = indexer.sync_all()
        item = db.get_by_rel_path(clean_filename)

        return {
            "status": "uploaded",
            "filename": clean_filename,
            "uploaded_by": user_id,
            "item": item.to_dict() if item else None,
            "sync_stats": stats,
        }

    # Mount modern SPA Web Interface
    repo_root = Path(__file__).resolve().parent.parent.parent
    web_dir = repo_root / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


def main():
    """Run standalone Uvicorn server."""
    import uvicorn

    setup_logger()
    cfg = MediaConfig()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
