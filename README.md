# Universal Personal Cloud Platform (USPC)

[![Tests](https://github.com/dayashimoga/USPC/actions/workflows/test.yml/badge.svg)](https://github.com/dayashimoga/USPC/actions/workflows/test.yml)
[![Security](https://github.com/dayashimoga/USPC/actions/workflows/security.yml/badge.svg)](https://github.com/dayashimoga/USPC/actions/workflows/security.yml)
[![Coverage](https://img.shields.io/badge/Coverage-%E2%89%A595%25-brightgreen.svg)](https://github.com/dayashimoga/USPC)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)

**Convert any Linux, Windows, or macOS machine into a secure personal cloud with one command.**

USPC deploys a fully self-hosted, encrypted, VPN-secured personal cloud (Nextcloud + PostgreSQL + Redis + USPC Media Engine) using Podman containers, WireGuard/Headscale networking, and Restic encrypted backups — with **zero vendor dependencies** and **100% free & open-source software**.

---

## Highlights & Features

| Capability | Implementation & Technology |
|---|---|
| **One-Command Bootstrap** | `cloudctl setup` (idempotent, reboot-safe, with `--dry-run` preflight) |
| **Files & Sync Engine** | Nextcloud Community (version-pinned `27.1.4`) with PostgreSQL 16 & Redis 7.2 |
| **Media Library & Player** | Unified Photos, Video & Audio streaming microservice (FastAPI + HTML5 + WebP) |
| **Instant Streaming** | HTTP 206 Partial Content range requests, chunked file I/O, instant seeking |
| **Private Mesh Access** | WireGuard + self-hosted Headscale overlay network (zero public port exposure) |
| **Adaptive Performance** | Automatic hardware profile detection (`TINY`, `SMALL`, `STANDARD`, `PERFORMANCE`, `MEDIA`) |
| **Multi-User Scalability** | Per-user stream limits, sliding-window rate limiting, and in-flight deduplication |
| **Encrypted Backups & DR** | Restic client-side AES-256 encrypted snapshots with integrity verification (`--verify`) |
| **Production Readiness** | 6-Layer audit engine (`cloudctl readiness`) and automated release gate (`cloudctl acceptance`) |
| **Zero Vendor Lock-in** | 100% Free & Open-Source, portable migration bundles (`cloudctl migrate`) |

---

## Quick Start (One-Command Setup)

```bash
# 1. Clone the repository
git clone https://github.com/dayashimoga/USPC.git
cd uspc


# 2. Automated one-command setup bootstrap (or add --dry-run to simulate)
./cloudctl setup

# 3. Execute automated production-acceptance lab and generate evidence reports
./cloudctl acceptance --full --output-dir reports/
```

---

## Command Reference

```text
cloudctl setup           # One-command automated bootstrap (--dry-run, --non-interactive, --force)
cloudctl acceptance      # Automated production-acceptance release gate (--full, --json, --output-dir)
cloudctl init            # Initialize configuration and security credentials
cloudctl install         # Full automated container stack installation
cloudctl start           # Start all cloud containers and services
cloudctl stop            # Stop all cloud containers and services
cloudctl restart         # Restart all cloud containers and services
cloudctl status          # Show system status and container health
cloudctl doctor          # Run diagnostic health checks with remediation (--fix)
cloudctl performance     # Display live CPU/RAM/Disk metrics, active streams, and profile
cloudctl benchmark       # Measure disk IO, compute score, and max stream throughput
cloudctl update          # Safe update with pre-flight snapshot and rollback
cloudctl backup          # Create encrypted Restic backup snapshot (--verify)
cloudctl restore         # Restore cloud state from snapshot (--dry-run, --test)
cloudctl migrate export  # Export portable migration bundle archive
cloudctl migrate import  # Import migration bundle onto new machine
cloudctl config          # Declarative config validate, diff (provenance), export, import, migrate
cloudctl readiness       # 6-Layer production readiness compliance evaluation (--json)
cloudctl uninstall       # Cleanly remove containers and networks
cloudctl logs            # Stream or inspect service logs

cloudctl security-check  # Run comprehensive security audit
cloudctl test            # Run automated test suite
cloudctl bundle create   # Create offline installation bundle
```

---

## Hardware Resource Profiles

USPC automatically scales its concurrency, connection pools, and cache sizes based on detected host resources:

- `TINY` (< 2.5GB RAM, 1 CPU Core): 2 max streams, 1 per user, no transcoding, 120 RPM rate limit.
- `SMALL` (2.5 - 5GB RAM, 2 Cores): 5 max streams, 2 per user, 1 transcode job, 300 RPM rate limit.
- `STANDARD` (5 - 10GB RAM, 4 Cores): 15 max streams, 3 per user, 2 transcode jobs, 600 RPM rate limit.
- `PERFORMANCE` (10 - 20GB RAM, 6+ Cores): 40 max streams, 5 per user, 4 transcode jobs, 1200 RPM rate limit.
- `MEDIA` (20GB+ RAM, 8+ Cores, NVMe): 100 max streams, 10 per user, 8 transcode jobs, 2400 RPM rate limit.

*All settings are fully overridable in `config/cloud.yaml`.*

---

## Testing & Quality Assurance

USPC enforces **≥95.0% meaningful code coverage and 100% passing tests** across all modules.

```bash
# Run full automated test suite
pytest --cov=src --cov-report=term-missing

# Run production-acceptance gate report
cloudctl acceptance --output-dir reports/

# Run code quality linter
ruff check src/ tests/
```

---

## Documentation

- [Technical Architecture Overview](docs/architecture/overview.md)
- [Security Architecture & Threat Model](docs/security/threat-model.md)
- [Production Readiness & Verification Matrix](docs/operations/readiness-matrix.md)
- [Linux Setup Guide](docs/setup/linux.md)
- [Windows Setup Guide](docs/setup/windows.md)
- [macOS Setup Guide](docs/setup/macos.md)
- [Performance & Scalability Guide](docs/operations/performance.md)
- [Configuration Reference](docs/operations/configuration.md)
- [Backup & Disaster Recovery Guide](docs/operations/backup-restore.md)
- [User Guide (Files & Media)](docs/user-guide/getting-started.md)
- [Supported Formats Matrix](docs/media/supported-formats.md)
- [Troubleshooting Runbook](docs/operations/troubleshooting.md)

---

## License

GNU Affero General Public License v3.0 ([AGPL-3.0](LICENSE))
