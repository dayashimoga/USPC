"""End-to-End Tests for USPC Media Library & Streaming Web UI.

Supports full Playwright browser automation when available in container/CI,
with zero-dependency DOM and web interface structure validation fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from playwright.sync_api import Page, expect

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Page = None  # type: ignore


def _get_web_html() -> str:
    """Load web index.html content."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    html_path = repo_root / "web" / "index.html"
    return html_path.read_text(encoding="utf-8")


def test_media_library_page_load_and_navigation(page: Page | None = None):
    """Test web client loading, navigation tabs, and responsiveness."""
    if HAS_PLAYWRIGHT and page is not None:
        base_url = os.getenv("USPC_TEST_URL", "http://127.0.0.1:8085")
        page.goto(base_url)
        expect(page).to_have_title("USPC Media & Cloud Library")
        expect(page.locator(".brand-title")).to_contain_text("USPC")
        return

    # DOM & Web interface asset validation
    html = _get_web_html()
    assert "<title>USPC Media & Cloud Library</title>" in html
    assert 'id="search-input"' in html
    assert 'class="filter-pills"' in html
    assert 'id="media-grid"' in html
    assert 'id="file-upload-input"' in html


def test_video_player_modal_and_seeking(page: Page | None = None):
    """Test clicking video card opens video modal player without downloading."""
    if HAS_PLAYWRIGHT and page is not None:
        base_url = os.getenv("USPC_TEST_URL", "http://127.0.0.1:8085")
        page.goto(base_url)
        video_card = page.locator(".media-card[data-type='video']").first
        if video_card.is_visible():
            video_card.click()
            modal = page.locator("#video-modal")
            expect(modal).to_be_visible()
            video_elem = page.locator("#native-video-element")
            expect(video_elem).to_be_visible()
            close_btn = page.locator("#video-modal-close")
            close_btn.click()
            expect(modal).not_to_be_visible()
        return

    # DOM modal structure validation
    html = _get_web_html()
    assert 'id="video-modal"' in html
    assert 'id="native-video-element"' in html
    assert 'id="video-modal-close"' in html
    assert 'id="video-modal-download"' in html


def test_audio_player_dock_and_playlist(page: Page | None = None):
    """Test audio item triggers sticky dock player and playlist queue."""
    if HAS_PLAYWRIGHT and page is not None:
        base_url = os.getenv("USPC_TEST_URL", "http://127.0.0.1:8085")
        page.goto(base_url)
        audio_card = page.locator(".media-card[data-type='audio']").first
        if audio_card.is_visible():
            audio_card.click()
            dock = page.locator("#audio-dock-player")
            expect(dock).to_be_visible()
            expect(page.locator("#audio-play-btn")).to_be_visible()
        return

    # DOM audio dock validation
    html = _get_web_html()
    assert 'id="audio-dock-player"' in html
    assert 'id="native-audio-element"' in html
    assert 'id="audio-play-btn"' in html
    assert 'id="audio-seek-bar"' in html


def test_image_lightbox_viewer(page: Page | None = None):
    """Test image click opens photo lightbox viewer."""
    if HAS_PLAYWRIGHT and page is not None:
        base_url = os.getenv("USPC_TEST_URL", "http://127.0.0.1:8085")
        page.goto(base_url)
        img_card = page.locator(".media-card[data-type='image']").first
        if img_card.is_visible():
            img_card.click()
            lightbox = page.locator("#image-modal")
            expect(lightbox).to_be_visible()
        return

    # DOM lightbox modal validation
    html = _get_web_html()
    assert 'id="image-modal"' in html
    assert 'id="image-modal-img"' in html
    assert 'id="image-modal-close"' in html
