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
| **Switchable Orchestration** | Podman Appliance Mode (default for single server) & K3s Cluster Mode (for 2+ nodes) |
| **Files & Sync Engine** | Nextcloud Community (version-pinned `27.1.4`) with PostgreSQL 16 & Redis 7.2 |
| **Media Library & Player** | Unified Photos, Video & Audio streaming microservice (FastAPI + HTML5 + WebP) |
| **Instant Streaming** | HTTP 206 Partial Content range requests, chunked file I/O, instant seeking, modern CSP |
| **Private Mesh Access** | WireGuard + self-hosted Headscale overlay network (zero public port exposure) |
| **Observability Stack** | Multi-tier monitoring profiles (`MINIMAL`, `STANDARD`, `FULL`, `CLUSTER`) with Prometheus, Grafana & Loki |
| **Hardware Auto-Tuning** | Automatic capacity profile derivation (`TINY` to `MEDIA`) and latency budget validation |
| **Multi-User Scalability** | Per-user stream limits, sliding-window rate limiting, and in-flight deduplication |
| **Encrypted Backups & DR** | Restic client-side AES-256 encrypted snapshots with integrity verification (`--verify`) |
| **Production Readiness** | 7-Layer audit engine (`cloudctl readiness`) and 12-Gate release lab (`cloudctl acceptance --full`) |
| **100% FOSS & SBOM** | SPDX 2.3 & CycloneDX 1.5 SBOM generator (`cloudctl sbom`), 0% SaaS vendor lock-in |

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
cloudctl acceptance      # Automated 12-gate production acceptance lab (--full, --json, --output-dir)
cloudctl orchestrator    # Switchable orchestration (status, switch, nodes, scale, manifests)
cloudctl monitor         # Live terminal telemetry & observability dashboard (--profile, --prometheus)
cloudctl alerts          # Inspect active operational threshold alerts (--fail-on-critical, --profile)
cloudctl sbom            # Generate SPDX/CycloneDX SBOM & license audit (--format cyclonedx, --audit)
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
cloudctl readiness       # 7-Layer production readiness compliance evaluation (--json)
cloudctl uninstall       # Cleanly remove containers and networks
cloudctl logs            # Stream or inspect service logs
cloudctl security-check  # Run comprehensive security audit
cloudctl test            # Run automated test suite
cloudctl bundle create   # Create offline installation bundle
```

---

## Configuration Precedence

USPC applies a deterministic 5-stage configuration precedence:
1. **`AUTO`**: Hardware-detected physical capacity limits (CPU, RAM, Disk).
2. **`DEFAULT`**: Base schema defaults from `config/defaults.yaml`.
3. **`PROFILE`**: Active environment profile (`appliance`, `cluster`, `dev`, `test`).
4. **`ENVIRONMENT`**: Operating system environment variables (`USPC_*`).
5. **`USER-OVERRIDE`**: Explicit settings defined in user `cloud.yaml` (highest priority).


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

### Core
- [Requirements](docs/REQUIREMENTS.md) — Functional, non-functional, platform, and acceptance criteria
- [Architecture](docs/ARCHITECTURE.md) — System design, data flow, components, ports, and manifests
- [Implementation](IMPLEMENTATION.md) — Detailed implementation notes
- [Project Status](PROJECT_STATUS.md) — Test metrics, capability matrix, known limitations
- [Changelog](CHANGELOG.md) — Version history

### Operations
- [CLI Reference](docs/CLI-REFERENCE.md) — Complete command reference (26 commands, all flags)
- [Configuration Reference](docs/CONFIGURATION.md) — All settings, schema, precedence, env vars
- [Monitoring & Observability](docs/MONITORING.md) — Profiles, metrics, alerts, Prometheus/Grafana/Loki
- [Performance & Tuning](docs/PERFORMANCE.md) — Profiles, budgets, benchmarks, load tests
- [Backup & Disaster Recovery](docs/BACKUP-DR.md) — Restic, RPO/RTO, retention, DR lifecycle
- [Upgrade & Migration](docs/UPGRADE-MIGRATION.md) — Updates, config migration, host migration
- [Troubleshooting](docs/TROUBLESHOOTING.md) — Symptom → Diagnosis → Fix tables

### Architecture
- [Orchestration](docs/ORCHESTRATION.md) — Podman Appliance vs K3s Cluster mode
- [Networking](docs/NETWORKING.md) — Headscale/WireGuard VPN, port matrix, firewall
- [Security](SECURITY.md) — Threat model, auth, headers, secrets, audit checks

### Compliance
- [SBOM & License](docs/SBOM-LICENSE.md) — SPDX/CycloneDX, dependency inventory, license policy
- [Dependencies](docs/DEPENDENCIES.md) — All runtime, dev, and external dependencies
- [Acceptance Framework](docs/ACCEPTANCE.md) — 14-gate production release gate
- [Testing](docs/TESTING.md) — 222 tests, coverage, evidence taxonomy
- [CI/CD Pipeline](docs/CI-CD.md) — GitHub Actions workflows

### Setup & Installation
- [Installation & Setup Guide](docs/SETUP.md) — One-command bootstrap, prerequisites, and automated lifecycle
- [Linux Setup](docs/setup/linux.md) | [Windows Setup](docs/setup/windows.md) | [macOS Setup](docs/setup/macos.md)

### Quality & Governance
- [Production Gap Matrix](docs/PRODUCTION-GAP-MATRIX.md) — Comprehensive 15-area forensic gap analysis and closure matrix
- [Documentation Status](DOCUMENTATION_STATUS.md) — Audit matrix of all documentation
- [User Guide](docs/USER_GUIDE.md) — Getting started, browsing, streaming, uploads
- [Supported Formats](docs/media/supported-formats.md) — Video, audio, image format matrix

---

## License

GNU Affero General Public License v3.0 ([AGPL-3.0](LICENSE))
