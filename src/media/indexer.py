"""Media indexer and processing coordinator."""

from __future__ import annotations

from cloudctl.core.logging import get_logger
from src.media.config import MediaConfig
from src.media.metadata import MetadataExtractor
from src.media.models import MediaDatabase, MediaItem
from src.media.scanner import ScannedFile, StorageScanner
from src.media.thumbnails import ThumbnailGenerator

logger = get_logger("media.indexer")


class MediaIndexer:
    """Coordinates filesystem scanning, metadata extraction, thumbnail generation, and database updates."""

    def __init__(self, config: MediaConfig, db: MediaDatabase):
        self.config = config
        self.db = db
        self.scanner = StorageScanner(config)
        self.metadata_extractor = MetadataExtractor()
        self.thumbnail_gen = ThumbnailGenerator(
            thumbnails_dir=config.thumbnails_dir,
            default_width=config.thumbnail_width,
        )

    def process_file(self, scanned: ScannedFile) -> MediaItem:
        """Extract metadata, generate thumbnail, and persist item."""
        meta = self.metadata_extractor.extract(scanned.abs_path)
        thumb_path = self.thumbnail_gen.generate(
            file_path=scanned.abs_path,
            item_id=scanned.id,
            media_type=meta.media_type,
            duration=meta.duration_seconds,
        )

        item = MediaItem(
            id=scanned.id,
            rel_path=scanned.rel_path,
            filename=scanned.filename,
            media_type=meta.media_type,
            mime_type=meta.mime_type,
            size_bytes=scanned.size_bytes,
            mtime=scanned.mtime,
            duration_seconds=meta.duration_seconds,
            width=meta.width,
            height=meta.height,
            title=meta.title or scanned.abs_path.stem,
            artist=meta.artist,
            album=meta.album,
            thumbnail_path=str(thumb_path) if thumb_path else None,
            processed=1,
        )
        self.db.upsert_item(item)
        return item

    def sync_all(self) -> dict[str, int]:
        """Perform a full sync: scan disk, process new/modified items, and prune removed items."""
        scanned_files = self.scanner.scan()
        scanned_ids: set[str] = set()

        added = 0
        updated = 0

        for sc in scanned_files:
            scanned_ids.add(sc.id)
            existing = self.db.get_by_id(sc.id)

            if existing is None:
                # New file
                self.process_file(sc)
                added += 1
            elif (
                existing.mtime != sc.mtime
                or existing.size_bytes != sc.size_bytes
                or existing.processed == 0
            ):
                # Modified file
                self.process_file(sc)
                updated += 1

        # Prune deleted files from DB
        db_ids = self.db.get_all_ids()
        removed_ids = db_ids - scanned_ids
        for r_id in removed_ids:
            self.db.delete_by_id(r_id)

        logger.info(
            f"Sync complete: {added} added, {updated} updated, {len(removed_ids)} removed, {len(scanned_files)} total."
        )
        return {
            "added": added,
            "updated": updated,
            "removed": len(removed_ids),
            "total": len(scanned_files),
        }
