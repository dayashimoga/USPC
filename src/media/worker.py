"""Background task worker for periodic media indexing."""

from __future__ import annotations

import asyncio

from cloudctl.core.logging import get_logger
from src.media.config import MediaConfig
from src.media.fairness import should_throttle_background_jobs
from src.media.indexer import MediaIndexer
from src.media.models import MediaDatabase

logger = get_logger("media.worker")


class BackgroundWorker:
    """Runs periodic and on-demand media library synchronization in the background."""

    def __init__(self, config: MediaConfig, db: MediaDatabase, interval_seconds: int = 30):
        self.config = config
        self.db = db
        self.interval_seconds = interval_seconds
        self.indexer = MediaIndexer(config, db)
        self._running = False
        self._task: asyncio.Task | None = None
        self._trigger_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background worker loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Media background worker started.")

    async def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        self._trigger_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Media background worker stopped.")

    def trigger_scan(self) -> None:
        """Signal the worker to execute an immediate sync."""
        self._trigger_event.set()

    async def _run_loop(self) -> None:
        """Worker loop executing periodic scans."""
        while self._running:
            try:
                if should_throttle_background_jobs():
                    logger.warning(
                        "System under heavy load (>85% CPU or >90% RAM). Throttling background media indexing."
                    )
                else:
                    # Run sync in thread pool to prevent blocking asyncio event loop
                    await asyncio.to_thread(self.indexer.sync_all)
            except Exception as e:
                logger.error(f"Error during background media sync: {e}")

            # Wait for next interval or manual trigger event
            try:
                await asyncio.wait_for(self._trigger_event.wait(), timeout=self.interval_seconds)
                self._trigger_event.clear()
            except asyncio.TimeoutError:
                pass
