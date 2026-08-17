# USPC Performance, Scalability & Resource Profiles

USPC is designed to adapt to hardware capabilities from single-board laptops up to multi-core rack servers with high-speed NVMe storage.

## Hardware Profiles

USPC auto-detects CPU cores, RAM, and storage throughput and applies an optimal profile:

| Profile | Target Environment | Max Concurrent Streams | Max Streams / User | Max Parallel Transcoding | DB Pool Size | Redis Cache | Request Rate Limit |
|---|---|---|---|---|---|---|---|
| **TINY** | < 2GB RAM, 1 CPU Core | 2 | 1 | 0 (Direct stream only) | 5 | 128 MB | 120 RPM |
| **SMALL** | 2 - 4GB RAM, 2 Cores | 5 | 2 | 1 | 10 | 256 MB | 300 RPM |
| **STANDARD** | 4 - 8GB RAM, 4 Cores | 15 | 3 | 2 | 25 | 512 MB | 600 RPM |
| **PERFORMANCE** | 8 - 16GB RAM, 6+ Cores | 40 | 5 | 4 | 50 | 1024 MB | 1200 RPM |
| **MEDIA** | 16GB+ RAM, 8+ Cores, NVMe | 100 | 10 | 8 | 100 | 2048 MB | 2400 RPM |

### Overriding Resource Profiles

To enforce a specific profile, update `config/cloud.yaml`:

```yaml
performance:
  profile: "performance" # auto | tiny | small | standard | performance | media
  max_concurrent_streams: 30
  max_streams_per_user: 4
  max_transcode_concurrency: 2
  rate_limit_requests_per_minute: 1000
```

---

## Live Performance Monitoring

Run live performance inspections anytime:

```bash
./cloudctl performance
```

Output includes CPU, RAM, Disk I/O, active streams, and detected bottlenecks:

```text
======================================================================
 USPC Live Performance & Capacity Monitor
======================================================================
 Resource Profile   : [STANDARD] - Standard personal cloud server (4 - 8GB RAM, 4 CPU Cores)
 CPU Utilization    : 12.4%
 Memory Usage       : 34.1% (5.4 GB / 16.0 GB)
 Free Storage Space : 142.8 GB (78.2% free)
 Active Streams     : 3 / 15
 Health State       : [PASS]

 System Bottlenecks : None detected (Capacity is balanced)
======================================================================
```

---

## Practical Hardware Benchmarking

Measure exact sequential read/write speeds, cryptographic compute capacity, and maximum stream throughput:

```bash
./cloudctl benchmark
```

```text
======================================================================
 USPC Hardware & Throughput Benchmark
======================================================================
 [BENCHMARK RESULTS - Profile: STANDARD]
  * Sequential Disk Write  : 245.8 MB/s
  * Sequential Disk Read   : 520.4 MB/s
  * Compute Hash Score     : 48.2 M-Ops/s
  * Max Stream Throughput  : ~364.2 MB/s
  * Recommended Streams    : 15 concurrent streams
  * Recommended Transcodes : 2 parallel jobs

 [STATUS: PASS] Storage and compute exceed baseline requirements.
======================================================================
```
