"""Unit tests for SQLite media models and database persistence."""

from pathlib import Path

from src.media.models import MediaDatabase, MediaItem


def test_media_database_crud(temp_dir: Path):
    db_file = temp_dir / "test_media.sqlite"
    db = MediaDatabase(db_file)

    # Insert item
    item1 = MediaItem(
        id="item_001",
        rel_path="movies/clip1.mp4",
        filename="clip1.mp4",
        media_type="video",
        mime_type="video/mp4",
        size_bytes=10485760,
        mtime=1700000000.0,
        duration_seconds=120.5,
        width=1920,
        height=1080,
        title="Sample Clip 1",
    )
    db.upsert_item(item1)

    # Fetch by ID & rel_path
    fetched = db.get_by_id("item_001")
    assert fetched is not None
    assert fetched.filename == "clip1.mp4"
    assert fetched.width == 1920

    fetched_path = db.get_by_rel_path("movies/clip1.mp4")
    assert fetched_path is not None
    assert fetched_path.id == "item_001"

    # Insert audio item
    item2 = MediaItem(
        id="item_002",
        rel_path="music/song1.mp3",
        filename="song1.mp3",
        media_type="audio",
        mime_type="audio/mpeg",
        size_bytes=5242880,
        mtime=1700000010.0,
        duration_seconds=210.0,
        title="My Song",
        artist="Awesome Artist",
        album="Great Album",
    )
    db.upsert_item(item2)

    # Query & filter
    all_items, total = db.list_items()
    assert total == 2
    assert len(all_items) == 2

    video_items, v_total = db.list_items(media_type="video")
    assert v_total == 1
    assert video_items[0].id == "item_001"

    audio_items, a_total = db.list_items(media_type="audio")
    assert a_total == 1
    assert audio_items[0].id == "item_002"

    # Search
    search_res, s_total = db.list_items(search="Awesome")
    assert s_total == 1
    assert search_res[0].artist == "Awesome Artist"

    # Sorting
    sorted_items, _ = db.list_items(sort_by="size_bytes", order="ASC")
    assert sorted_items[0].id == "item_002"  # 5MB before 10MB

    # Deletion
    assert db.delete_by_id("item_001") is True
    assert db.get_by_id("item_001") is None
    assert db.delete_by_id("item_001") is False
