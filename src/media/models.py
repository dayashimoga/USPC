import contextlib
import sqlite3
from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class MediaItem:
    """Represents an indexed media file."""

    id: str  # SHA256 of relative path
    rel_path: str
    filename: str
    media_type: str  # video, audio, image
    mime_type: str
    size_bytes: int
    mtime: float
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    thumbnail_path: str | None = None
    transcoded_path: str | None = None
    processed: int = 0
    indexed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MediaDatabase:
    """Thread-safe SQLite database manager for media metadata and indices."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize SQLite database tables and indexes."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
                    rel_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    duration_seconds REAL,
                    width INTEGER,
                    height INTEGER,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    thumbnail_path TEXT,
                    transcoded_path TEXT,
                    processed INTEGER DEFAULT 0,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_items(media_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON media_items(filename)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mtime ON media_items(mtime)")
            conn.commit()

    def upsert_item(self, item: MediaItem) -> None:
        """Insert or update media item."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO media_items (
                    id, rel_path, filename, media_type, mime_type, size_bytes, mtime,
                    duration_seconds, width, height, title, artist, album,
                    thumbnail_path, transcoded_path, processed
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(rel_path) DO UPDATE SET
                    filename=excluded.filename,
                    media_type=excluded.media_type,
                    mime_type=excluded.mime_type,
                    size_bytes=excluded.size_bytes,
                    mtime=excluded.mtime,
                    duration_seconds=excluded.duration_seconds,
                    width=excluded.width,
                    height=excluded.height,
                    title=excluded.title,
                    artist=excluded.artist,
                    album=excluded.album,
                    thumbnail_path=excluded.thumbnail_path,
                    transcoded_path=excluded.transcoded_path,
                    processed=excluded.processed
            """,
                (
                    item.id,
                    item.rel_path,
                    item.filename,
                    item.media_type,
                    item.mime_type,
                    item.size_bytes,
                    item.mtime,
                    item.duration_seconds,
                    item.width,
                    item.height,
                    item.title,
                    item.artist,
                    item.album,
                    item.thumbnail_path,
                    item.transcoded_path,
                    item.processed,
                ),
            )
            conn.commit()

    def get_by_id(self, item_id: str) -> MediaItem | None:
        """Fetch media item by unique ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_items WHERE id = ?", (item_id,)).fetchone()
            if row:
                return MediaItem(**dict(row))
        return None

    def get_by_rel_path(self, rel_path: str) -> MediaItem | None:
        """Fetch media item by relative path."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM media_items WHERE rel_path = ?", (rel_path,)
            ).fetchone()
            if row:
                return MediaItem(**dict(row))
        return None

    def list_items(
        self,
        media_type: str | None = None,
        search: str | None = None,
        sort_by: str = "mtime",
        order: str = "DESC",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[MediaItem], int]:
        """Query media items with filtering, search, sorting, and pagination."""
        query = "SELECT * FROM media_items WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM media_items WHERE 1=1"
        params: list[Any] = []

        if media_type and media_type in ("video", "audio", "image"):
            query += " AND media_type = ?"
            count_query += " AND media_type = ?"
            params.append(media_type)

        if search:
            search_pattern = f"%{search.strip()}%"
            query += " AND (filename LIKE ? OR title LIKE ? OR artist LIKE ? OR album LIKE ?)"
            count_query += " AND (filename LIKE ? OR title LIKE ? OR artist LIKE ? OR album LIKE ?)"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

        # Validate sorting column
        allowed_sort = {"filename", "size_bytes", "mtime", "duration_seconds", "indexed_at"}
        sort_col = sort_by if sort_by in allowed_sort else "mtime"
        sort_dir = "ASC" if order.upper() == "ASC" else "DESC"

        with self._get_connection() as conn:
            total_count = conn.execute(count_query, params).fetchone()[0]

            query += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
            full_params = params + [limit, offset]
            rows = conn.execute(query, full_params).fetchall()
            items = [MediaItem(**dict(r)) for r in rows]

        return items, total_count

    def delete_by_id(self, item_id: str) -> bool:
        """Remove item from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM media_items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_ids(self) -> set[str]:
        """Retrieve all indexed IDs (useful for purging deleted files)."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id FROM media_items").fetchall()
            return {r[0] for r in rows}
