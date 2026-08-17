"""Multi-user concurrent load, fairness, and capacity limits integration tests."""

import pytest
from fastapi import HTTPException

from cloudctl.core.performance import (
    LivePerformanceMetrics,
    collect_live_metrics,
    detect_resource_profile,
)
from src.media.fairness import ConcurrencyManager, SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_graduated_multiuser_concurrency_slots():
    """Verify concurrency manager scales across 1, 5, 10, 20 users and enforces fairness."""
    cm = ConcurrencyManager(max_global_streams=20, max_streams_per_user=3)

    # 1. Single user can acquire up to max_streams_per_user (3)
    for i in range(3):
        await cm.acquire_stream_slot("alice", f"alice_stream_{i}")
    assert cm.get_total_active_streams() == 3

    # Alice 4th stream must fail (HTTP 429)
    with pytest.raises(HTTPException) as exc_info:
        await cm.acquire_stream_slot("alice", "alice_stream_4")
    assert exc_info.value.status_code == 429
    assert "User streaming limit reached" in exc_info.value.detail

    # 2. Other users can acquire slots without being starved by Alice
    for u_idx in range(5):
        user_name = f"user_{u_idx}"
        await cm.acquire_stream_slot(user_name, f"{user_name}_stream_1")
    assert cm.get_total_active_streams() == 8

    # 3. Global capacity limit enforcement
    # Fill remaining 12 slots
    for u_idx in range(5, 17):
        user_name = f"user_{u_idx}"
        await cm.acquire_stream_slot(user_name, f"{user_name}_stream_1")
    assert cm.get_total_active_streams() == 20

    # 21st stream globally must fail with 429
    with pytest.raises(HTTPException) as exc_info:
        await cm.acquire_stream_slot("bob", "bob_stream_1")
    assert exc_info.value.status_code == 429
    assert "Server streaming capacity full" in exc_info.value.detail

    # 4. Releasing slot frees up space immediately
    await cm.release_stream_slot("alice", "alice_stream_0")
    assert cm.get_total_active_streams() == 19

    # Now Bob can acquire
    await cm.acquire_stream_slot("bob", "bob_stream_1")
    assert cm.get_total_active_streams() == 20


@pytest.mark.asyncio
async def test_rate_limiter_burst_and_recovery():
    """Verify rate limiter allows requests up to max_rpm and rejects excess."""
    limiter = SlidingWindowRateLimiter(max_requests_per_minute=10)
    client_ip = "192.168.1.50"

    # First 10 requests pass
    for _ in range(10):
        await limiter.check_rate_limit(client_ip)

    # 11th request must fail with 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit(client_ip)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "10"


def test_capacity_profiles_and_measured_reporting(tmp_path):
    """Verify profiles distinguish configured vs detected vs current capacity."""
    profile_tiny = detect_resource_profile("TINY")
    assert profile_tiny.name == "TINY"
    assert profile_tiny.max_concurrent_streams == 2

    profile_media = detect_resource_profile("MEDIA")
    assert profile_media.name == "MEDIA"
    assert profile_media.max_concurrent_streams == 100

    # Live metrics snapshot
    metrics = collect_live_metrics(tmp_path, active_streams=5, queue_depth=2)
    assert isinstance(metrics, LivePerformanceMetrics)
    assert metrics.active_streams == 5
    assert metrics.queue_depth == 2
    assert metrics.status in ("PASS", "WARN", "CRITICAL")
