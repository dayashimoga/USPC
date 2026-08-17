"""Unit tests for multi-user fairness, concurrency limits, and deduplication."""

import asyncio

import pytest
from fastapi import HTTPException

from src.media.fairness import (
    ConcurrencyManager,
    InFlightDeduplicator,
    SlidingWindowRateLimiter,
    should_throttle_background_jobs,
)


@pytest.mark.asyncio
async def test_concurrency_manager():
    mgr = ConcurrencyManager(max_global_streams=3, max_streams_per_user=2)

    # User 1 acquires 2 streams (OK)
    await mgr.acquire_stream_slot("user1", "stream_1a")
    await mgr.acquire_stream_slot("user1", "stream_1b")
    assert mgr.get_total_active_streams() == 2

    # User 1 tries 3rd stream -> 429 Limit reached
    with pytest.raises(HTTPException) as exc:
        await mgr.acquire_stream_slot("user1", "stream_1c")
    assert exc.value.status_code == 429

    # User 2 acquires 1 stream (Total = 3, Global Limit reached)
    await mgr.acquire_stream_slot("user2", "stream_2a")
    assert mgr.get_total_active_streams() == 3

    # User 3 tries stream -> 429 Global Limit reached
    with pytest.raises(HTTPException) as exc_glob:
        await mgr.acquire_stream_slot("user3", "stream_3a")
    assert exc_glob.value.status_code == 429

    # User 1 releases one stream -> User 3 can now acquire
    await mgr.release_stream_slot("user1", "stream_1a")
    assert mgr.get_total_active_streams() == 2
    await mgr.acquire_stream_slot("user3", "stream_3a")
    assert mgr.get_total_active_streams() == 3


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = SlidingWindowRateLimiter(max_requests_per_minute=5)

    # 5 requests pass
    for _ in range(5):
        await limiter.check_rate_limit("client_ip_1")

    # 6th request fails
    with pytest.raises(HTTPException) as exc:
        await limiter.check_rate_limit("client_ip_1")
    assert exc.value.status_code == 429

    # Different client is unaffected
    await limiter.check_rate_limit("client_ip_2")


@pytest.mark.asyncio
async def test_inflight_deduplication():
    dedup = InFlightDeduplicator()
    call_count = 0

    async def expensive_task():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return f"result_{call_count}"

    # Launch 4 concurrent requests for the exact same key
    results = await asyncio.gather(
        dedup.execute_or_join("thumb:video_123", expensive_task),
        dedup.execute_or_join("thumb:video_123", expensive_task),
        dedup.execute_or_join("thumb:video_123", expensive_task),
        dedup.execute_or_join("thumb:video_123", expensive_task),
    )

    # Only 1 execution occurred!
    assert call_count == 1
    assert all(r == "result_1" for r in results)


def test_system_load_watcher():
    res = should_throttle_background_jobs()
    assert isinstance(res, bool)
