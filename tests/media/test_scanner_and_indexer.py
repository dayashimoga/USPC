"""Unit tests for storage scanner, metadata extractor, and thumbnail generator."""

from pathlib import Path

from src.media.config import MediaConfig
from src.media.indexer import MediaIndexer
from src.media.metadata import MetadataExtractor, detect_media_type_and_mime
from src.media.models import MediaDatabase
from src.media.scanner import StorageScanner
from src.media.thumbnails import ThumbnailGenerator


def test_mime_and_type_detection(sample_media_files: dict[str, Path]):
    t_img, m_img = detect_media_type_and_mime(sample_media_files["image"])
    assert t_img == "image"
    assert "image/" in m_img

    t_vid, m_vid = detect_media_type_and_mime(sample_media_files["video"])
    assert t_vid == "video"
    assert "video/" in m_vid

    t_aud, m_aud = detect_media_type_and_mime(sample_media_files["audio"])
    assert t_aud == "audio"
    assert "audio/" in m_aud


def test_metadata_extraction(sample_media_files: dict[str, Path]):
    extractor = MetadataExtractor()

    # Image metadata
    img_meta = extractor.extract(sample_media_files["image"])
    assert img_meta.media_type == "image"
    assert img_meta.width == 640
    assert img_meta.height == 480

    # Video metadata
    vid_meta = extractor.extract(sample_media_files["video"])
    assert vid_meta.media_type == "video"


def test_thumbnail_generation(sample_media_files: dict[str, Path], temp_dir: Path):
    thumbs_dir = temp_dir / "thumbs"
    gen = ThumbnailGenerator(thumbnails_dir=thumbs_dir, default_width=320)

    # Generate image thumbnail
    thumb = gen.generate(sample_media_files["image"], "item_img_1", "image")
    assert thumb is not None
    assert thumb.exists()
    assert thumb.suffix == ".webp"

    # Generate video poster thumbnail
    vid_thumb = gen.generate(sample_media_files["video"], "item_vid_1", "video", duration=15.0)
    assert vid_thumb is not None
    assert vid_thumb.exists()

    # Generate audio badge thumbnail
    aud_thumb = gen.generate(sample_media_files["audio"], "item_aud_1", "audio")
    assert aud_thumb is not None
    assert aud_thumb.exists()


def test_scanner_and_indexer_sync(media_test_env: tuple[MediaConfig, MediaDatabase]):
    cfg, db = media_test_env
    scanner = StorageScanner(cfg)
    scanned = scanner.scan()
    assert len(scanned) >= 4

    indexer = MediaIndexer(cfg, db)
    sync_stats = indexer.sync_all()
    assert sync_stats["added"] >= 4
    assert sync_stats["total"] >= 4

    # Verify items in database
    items, total = db.list_items()
    assert total >= 4
    assert any(i.filename == "test_photo.jpg" for i in items)
    assert any(i.filename == "test_video.mp4" for i in items)
