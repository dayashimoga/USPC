"""Historical metrics tracking and vendor-free alerting using SQLite."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import ensure_directory

logger = get_logger("metrics")


@dataclass
class MetricSnapshot:
    """A timestamped performance and operational metric snapshot."""

    timestamp: float
    cpu_percent: float
    ram_percent: float
    disk_free_gb: float
    active_streams: int
    queue_depth: int
    error_count: int = 0


class MetricsStore:
    """Manages lightweight, self-contained time-series metrics in SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(db_path).expanduser().resolve()
        else:
            self.db_path = Path("~/.uspc/data/metrics/metrics.sqlite").expanduser().resolve()
        ensure_directory(self.db_path.parent)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metric_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        cpu_percent REAL NOT NULL,
                        ram_percent REAL NOT NULL,
                        disk_free_gb REAL NOT NULL,
                        active_streams INTEGER NOT NULL,
                        queue_depth INTEGER NOT NULL,
                        error_count INTEGER NOT NULL DEFAULT 0
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metric_snapshots(timestamp)"
                )
        except sqlite3.DatabaseError:
            logger.warning(
                f"Corrupted metrics database detected at {self.db_path}. Resetting database..."
            )
            if self.db_path.exists():
                self.db_path.unlink(missing_ok=True)
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metric_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        cpu_percent REAL NOT NULL,
                        ram_percent REAL NOT NULL,
                        disk_free_gb REAL NOT NULL,
                        active_streams INTEGER NOT NULL,
                        queue_depth INTEGER NOT NULL,
                        error_count INTEGER NOT NULL DEFAULT 0
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metric_snapshots(timestamp)"
                )

    def record_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Insert a new metrics snapshot record."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO metric_snapshots
                (timestamp, cpu_percent, ram_percent, disk_free_gb, active_streams, queue_depth, error_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp,
                    snapshot.cpu_percent,
                    snapshot.ram_percent,
                    snapshot.disk_free_gb,
                    snapshot.active_streams,
                    snapshot.queue_depth,
                    snapshot.error_count,
                ),
            )

    def get_historical_summary(self, window_hours: float = 1.0) -> dict[str, Any]:
        """Compute average, min, and max metrics over the given time window."""
        cutoff = time.time() - (window_hours * 3600)
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as sample_count,
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(ram_percent) as avg_ram,
                    MAX(ram_percent) as max_ram,
                    MIN(disk_free_gb) as min_disk_free,
                    MAX(active_streams) as peak_streams,
                    SUM(error_count) as total_errors
                FROM metric_snapshots
                WHERE timestamp >= ?
                """,
                (cutoff,),
            ).fetchone()

            if not row or row["sample_count"] == 0:
                return {
                    "window_hours": window_hours,
                    "sample_count": 0,
                    "avg_cpu": 0.0,
                    "max_cpu": 0.0,
                    "avg_ram": 0.0,
                    "max_ram": 0.0,
                    "min_disk_free_gb": 0.0,
                    "peak_streams": 0,
                    "total_errors": 0,
                }

            return {
                "window_hours": window_hours,
                "sample_count": row["sample_count"],
                "avg_cpu": round(row["avg_cpu"] or 0.0, 1),
                "max_cpu": round(row["max_cpu"] or 0.0, 1),
                "avg_ram": round(row["avg_ram"] or 0.0, 1),
                "max_ram": round(row["max_ram"] or 0.0, 1),
                "min_disk_free_gb": round(row["min_disk_free"] or 0.0, 1),
                "peak_streams": row["peak_streams"] or 0,
                "total_errors": row["total_errors"] or 0,
            }

    def check_alerts(self, min_disk_gb: float = 5.0) -> list[str]:
        """Inspect recent metrics (last 5 minutes) and generate automated alert warnings."""
        summary = self.get_historical_summary(window_hours=0.083)  # ~5 min
        alerts: list[str] = []

        if summary["sample_count"] > 0:
            if summary["max_cpu"] > 90.0:
                alerts.append(f"CRITICAL: Peak CPU reached {summary['max_cpu']}% in last 5m")
            elif summary["avg_cpu"] > 80.0:
                alerts.append(f"WARNING: Sustained high CPU load ({summary['avg_cpu']}%)")

            if summary["max_ram"] > 92.0:
                alerts.append(f"CRITICAL: Peak RAM reached {summary['max_ram']}% in last 5m")

            if summary["min_disk_free_gb"] < min_disk_gb:
                alerts.append(
                    f"WARNING: Low disk space detected ({summary['min_disk_free_gb']} GB < {min_disk_gb} GB)"
                )

            if summary["total_errors"] > 10:
                alerts.append(
                    f"WARNING: Elevated error rate ({summary['total_errors']} errors in last 5m)"
                )

        return alerts

    def get_db_size_bytes(self) -> int:
        """Return the size of the SQLite metrics database in bytes."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def enforce_storage_limit(self, max_size_bytes: int = 100 * 1024 * 1024) -> bool:
        """
        Ensure metrics database never exceeds maximum allocated storage.
        If file exceeds max_size_bytes, aggressively prune older records and VACUUM.
        """
        if self.get_db_size_bytes() > max_size_bytes:
            logger.warning(
                f"Metrics store ({self.get_db_size_bytes()} bytes) exceeds limit ({max_size_bytes} bytes). Pruning records..."
            )
            # Prune down to 7 days
            self.prune_old_metrics(retention_days=7)
            with self._get_connection() as conn:
                conn.execute("VACUUM")
            return True
        return False

    def prune_old_metrics(self, retention_days: int = 30) -> int:
        """Prune snapshots older than retention threshold to conserve storage."""
        cutoff = time.time() - (retention_days * 86400)
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM metric_snapshots WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted


def format_prometheus_metrics(
    snapshot: MetricSnapshot, extra_gauges: dict[str, float] | None = None
) -> str:
    """Format a snapshot into standard Prometheus exposition text format."""
    lines = [
        "# HELP uspc_cpu_utilization_percent Current CPU utilization percentage.",
        "# TYPE uspc_cpu_utilization_percent gauge",
        f"uspc_cpu_utilization_percent {snapshot.cpu_percent:.2f}",
        "",
        "# HELP uspc_memory_utilization_percent Current RAM utilization percentage.",
        "# TYPE uspc_memory_utilization_percent gauge",
        f"uspc_memory_utilization_percent {snapshot.ram_percent:.2f}",
        "",
        "# HELP uspc_disk_free_gigabytes Free disk storage on data volume in GB.",
        "# TYPE uspc_disk_free_gigabytes gauge",
        f"uspc_disk_free_gigabytes {snapshot.disk_free_gb:.2f}",
        "",
        "# HELP uspc_active_streams Number of active concurrent media streams.",
        "# TYPE uspc_active_streams gauge",
        f"uspc_active_streams {snapshot.active_streams}",
        "",
        "# HELP uspc_transcoder_queue_depth Pending video/audio transcoding jobs in worker queue.",
        "# TYPE uspc_transcoder_queue_depth gauge",
        f"uspc_transcoder_queue_depth {snapshot.queue_depth}",
        "",
        "# HELP uspc_errors_total Cumulative or windowed error count.",
        "# TYPE uspc_errors_total counter",
        f"uspc_errors_total {snapshot.error_count}",
    ]
    if extra_gauges:
        for k, v in extra_gauges.items():
            safe_k = k.replace("-", "_").replace(".", "_")
            lines.extend(
                [
                    "",
                    f"# HELP uspc_{safe_k} Operational metric for {safe_k}.",
                    f"# TYPE uspc_{safe_k} gauge",
                    f"uspc_{safe_k} {v}",
                ]
            )
    return "\n".join(lines) + "\n"
