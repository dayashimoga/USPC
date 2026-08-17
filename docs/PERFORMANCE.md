# USPC Performance

> Module: `src/cloudctl/core/performance.py`

## Hardware Profiles

USPC auto-detects host resources and selects an appropriate profile:

| Profile | RAM | CPU Cores | Max Streams | Per-User | Transcode | Rate Limit (RPM) |
|---|---|---|---|---|---|---|
| `TINY` | < 2.5 GB | 1 | 2 | 1 | 0 | 120 |
| `SMALL` | 2.5–5 GB | 2 | 5 | 2 | 1 | 300 |
| `STANDARD` | 5–10 GB | 4 | 15 | 3 | 2 | 600 |
| `PERFORMANCE` | 10–20 GB | 6+ | 40 | 5 | 4 | 1200 |
| `MEDIA` | 20+ GB | 8+ | 100 | 10 | 8 | 2400 |

Auto-tuning is controlled by `performance.auto_tune: true` (default). Override with `performance.profile: <name>`.

---

## Performance Budgets

| Metric | Budget | Source |
|---|---|---|
| API listing P95 latency | ≤ 50 ms | `budgets.max_listing_p95_ms` |
| Media stream start P95 | ≤ 100 ms | `budgets.max_stream_start_p95_ms` |
| API P99 latency | ≤ 200 ms | `budgets.max_api_p99_ms` |
| Service startup time | ≤ 30 s | `budgets.max_startup_seconds` |
| Upload throughput | ≥ 10 MB/s | `budgets.min_upload_throughput_mb_s` |
| Max concurrent users | 50 | `budgets.max_concurrent_users` |
| Soak RSS drift | < 5 MB/hour | Soak test measurement |

---

## Benchmark Commands

```bash
# Auto-detect profile and benchmark
cloudctl benchmark

# Force specific profile
cloudctl benchmark --profile performance

# Execute named load profile
cloudctl benchmark --load-profile heavy

# Progressive stress test
cloudctl benchmark --stress

# Sustained soak endurance test (3 seconds default)
cloudctl benchmark --soak --duration 10

# JSON output
cloudctl benchmark --json
```

### Load Profiles

| Profile | Description |
|---|---|
| `smoke` | Minimal validation pass |
| `normal` | Typical workload simulation |
| `heavy` | High concurrency |
| `media_heavy` | Media-intensive streaming |
| `multi_user` | Multiple simultaneous users |
| `stress` | Progressive overload |
| `soak` | Long-duration endurance |

---

## Live Metrics

```bash
# Live CPU/RAM/disk/streams dashboard
cloudctl performance

# JSON output
cloudctl performance --json
```

---

## Concurrency Control

| Mechanism | Module | Default |
|---|---|---|
| Global stream limit | `ConcurrencyManager` | Auto-tuned per profile |
| Per-user stream limit | `ConcurrencyManager` | Auto-tuned per profile |
| Per-IP rate limit | `SlidingWindowRateLimiter` | 600 RPM (configurable) |
| In-flight deduplication | `InFlightDeduplicator` | Prevents duplicate stream requests |
| Background load shedding | `BackgroundWorker` | Pauses tasks at > 85% CPU / 90% RAM |

---

## Cross-References

- [Configuration](CONFIGURATION.md) | [Monitoring](MONITORING.md) | [Architecture](ARCHITECTURE.md)
- [Testing](TESTING.md) | [Acceptance](ACCEPTANCE.md)
