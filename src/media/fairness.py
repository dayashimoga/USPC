"""Fairness, concurrency limits, rate limiting, and in-flight deduplication."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import psutil
from fastapi import HTTPException, status

from cloudctl.core.logging import get_logger

logger = get_logger("media.fairness")


class ConcurrencyManager:
    """Enforces global and per-user streaming concurrency limits."""

    def __init__(self, max_global_streams: int = 15, max_streams_per_user: int = 3):
        self.max_global_streams = max_global_streams
        self.max_streams_per_user = max_streams_per_user
        self.active_streams: dict[str, set[str]] = defaultdict(set)  # user_id -> set of stream_ids
        self._lock = asyncio.Lock()

    async def acquire_stream_slot(self, user_id: str, stream_id: str) -> None:
        """Reserve a streaming slot for a user or raise 429 / 503."""
        async with self._lock:
            # Check global capacity
            total_active = sum(len(s) for s in self.active_streams.values())
            if total_active >= self.max_global_streams:
                logger.warning(
                    f"Global stream limit reached ({total_active}/{self.max_global_streams})"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Server streaming capacity full. Please try again shortly.",
                    headers={"Retry-After": "5"},
                )

            # Check per-user capacity
            user_active = len(self.active_streams[user_id])
            if user_active >= self.max_streams_per_user:
                logger.warning(
                    f"User '{user_id}' stream limit reached ({user_active}/{self.max_streams_per_user})"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"User streaming limit reached ({self.max_streams_per_user} concurrent streams).",
                    headers={"Retry-After": "5"},
                )

            self.active_streams[user_id].add(stream_id)

    async def release_stream_slot(self, user_id: str, stream_id: str) -> None:
        """Free streaming slot on stream completion or disconnect."""
        async with self._lock:
            if user_id in self.active_streams:
                self.active_streams[user_id].discard(stream_id)
                if not self.active_streams[user_id]:
                    del self.active_streams[user_id]

    def get_total_active_streams(self) -> int:
        return sum(len(s) for s in self.active_streams.values())


class SlidingWindowRateLimiter:
    """Per-IP / Per-user request rate limiter."""

    def __init__(self, max_requests_per_minute: int = 600):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, client_id: str) -> None:
        """Validate client request frequency."""
        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            # Clean old requests
            reqs = [t for t in self.requests[client_id] if t > cutoff]
            if len(reqs) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="API rate limit exceeded. Please slow down requests.",
                    headers={"Retry-After": "10"},
                )
            reqs.append(now)
            self.requests[client_id] = reqs


class InFlightDeduplicator:
    """Deduplicates simultaneous heavy operations (e.g. thumbnail creation for same item)."""

    def __init__(self):
        self._in_flight: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def execute_or_join(
        self, key: str, coro_func: Callable[[], Coroutine[Any, Any, Any]]
    ) -> Any:
        """Run expensive async task once, allowing all concurrent callers to share result."""
        async with self._lock:
            if key in self._in_flight:
                future = self._in_flight[key]
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._in_flight[key] = future

                # Spawn task
                asyncio.create_task(self._run_task(key, future, coro_func))

        return await asyncio.shield(future)

    async def _run_task(
        self, key: str, future: asyncio.Future, coro_func: Callable[[], Coroutine[Any, Any, Any]]
    ) -> None:
        try:
            result = await coro_func()
            if not future.done():
                future.set_result(result)
        except Exception as e:
            if not future.done():
                future.set_exception(e)
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)


def should_throttle_background_jobs() -> bool:
    """Check if host system is under heavy load (>85% CPU or >90% RAM)."""
    try:
        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory().percent
        return cpu > 85.0 or mem > 90.0
    except Exception:
        return False
