# Changelog

All notable changes to the Universal Personal Cloud Platform (USPC) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-17
### Production Acceptance Hardening & Multi-Layer Audit Release
- **Unified Bootstrap Command (`cloudctl setup`)**:
  - Implemented `cloudctl setup` for zero-overhead one-command bootstrap across Linux, Windows (WSL2/Docker), and macOS.
  - Added `--dry-run`, `--non-interactive`, and `--force` flags with idempotent, reboot-safe execution.
- **Enhanced Configuration & Version Migrations**:
  - Added `get_setting_metadata` exposing description, allowed ranges/enums, restart requirements, and security impacts for every configuration key.
  - Added `cloudctl config migrate` for automated schema and version transitions.
- **Security Attack Resilience & Timing Attack Protection**:
  - Added clock skew tolerance parameter (`clock_skew_seconds`) with default strictness.
  - Enforced constant-time secret comparison (`hmac.compare_digest`) across master admin tokens and query HMAC verification.
  - Added comprehensive security attack test suite (`test_security_attacks.py`) testing IDOR, encoded path traversals, Windows reserved filenames, token forgery, replay, and secret rotation.
- **Infrastructure & Resource Failure Injection**:
  - Added `test_resilience.py` testing database outages, Redis cache failures, container crashes, disk-full protection, and high-load shedding (>85% CPU / >90% RAM).
  - Added auto-recovery in `MetricsStore` for corrupted database files.
- **5-Layer Production Readiness Audit**:
  - Restructured `cloudctl readiness` into 5 explicit evaluation layers: Infrastructure, Application, Security, Recovery, and Observability.
  - Added storage limit enforcement and auto-vacuuming for metrics database.
- **Playwright Containerized E2E & Network Mesh Testing**:
  - Added containerized Playwright browser E2E test harness (`tests/e2e/Dockerfile`, `test_browser_media.py`).
  - Added simulated cross-network Headscale/WireGuard peer enrollment test suite (`test_network_mesh.py`).
- **Test Suite Scale & Coverage**:
  - Expanded test suite to **172 automated tests** passing at **100%** with **95.58% overall code coverage**.
  - Reclassified all capabilities to precise empirical labels (`UNIT-PROVEN`, `INTEGRATION-PROVEN`, `CONTAINER-PROVEN`, `VM-PROVEN`, `BROWSER-PROVEN`, `HARDWARE-REQUIRED`).

## [0.3.0] - 2026-08-17
### Final Production Hardening & Readiness Release
- **Security & Authorization Overhaul**:
  - Eliminated raw secret query parameter bypass from `authenticate_request` in `src/media/auth.py`.
  - Added in-memory cryptographic token revocation registry (`revoke_token`, `is_token_revoked`, `clear_revoked_tokens`).
  - Added request correlation tracking (`X-Request-ID` and UUID4 state assignment).
  - Added automated dependency vulnerability scanning (`pip-audit`) in GitHub Actions security workflow.
- **Production Readiness & Observability (`cloudctl readiness`)**:
  - Implemented `cloudctl readiness` command performing comprehensive multi-subsystem audits with `PRODUCTION_READY`, `READY`, `DEGRADED`, and `NOT_READY` verdicts.
  - Implemented ultra-lightweight SQLite historical time-series metric store (`MetricsStore`) capturing CPU%, RAM%, disk, active streams, and queue depths with 30-day retention pruning.
  - Added automated threshold alert evaluation (CPU >90%, RAM >92%, Disk <5GB, error spikes).
- **Declarative Configuration Management (`cloudctl config`)**:
  - Implemented `cloudctl config validate|diff|export|import` with leaf-level provenance tracking (`AUTO`, `DEFAULT`, `USER-OVERRIDE`).
  - Added safe configuration export with automated secret masking (`cloudctl config export`).
  - Added atomic configuration import with automated backup creation (`cloudctl config import`).
- **Benchmarking & Stress Workloads**:
  - Added 4KB random IOPS and latency percentile measurements (P50/P95/P99 ms) in `run_benchmark`.
  - Added progressive concurrency stress testing (`cloudctl benchmark --stress`) to empirically measure host limits under concurrent load.
- **Test Suite & Verification Expansion**:
  - Test suite expanded to **140 automated tests** passing at **100%** with **95.76% overall code coverage**.
  - Published comprehensive production readiness and verification matrix in `docs/operations/readiness-matrix.md`.

## [0.2.0] - 2026-08-17

### Security & Reliability Hardening
- **Authentication & IDOR Protection**:
  - Enforced `Depends(authenticate_request)` across all media endpoints (`/api/media/{id}/stream`, `/api/media/{id}/download`, `/api/upload`, `/api/scan`).
  - Added user extraction and cryptographic item-id validation to prevent IDOR attacks.
- **Fairness & Concurrency Management**:
  - Wired `ConcurrencyManager` stream slot tracking directly into media streaming pipeline.
  - Active sliding-window per-IP rate limiting middleware.
  - Background task load shedding when system load exceeds 85% CPU / 90% RAM.
- **Vulnerability Remediations**:
  - Safe Tar member path validation during migration bundle imports (CVE-2007-4559 tar slip remediation).
  - Explicit symlink escape protection in media storage scanner.
  - Upload file size constraints (`max_upload_size_mb`) and filename sanitization.
  - Elimination of FastAPI HTTP 416 deprecation warnings.
- **New Operations Tooling**:
  - New `cloudctl cleanup` command for safe inspection and reclamation of thumbnail and transcode caches.
  - Automated Restic retention pruning (`BackupManager.prune_retention`).
  - Storage breakdown metrics (`StorageManager.get_usage_stats`).
- **Quality & Test Coverage**:
  - Raised test suite to **115 passing tests** with **95.21% code coverage** (100% in secrets, reporting, install, bundle, benchmark, models).
  - Enforced `fail_under = 95` in `pyproject.toml` and CI test workflow.

## [0.1.0] - 2026-08-17

### Added
- **Core CLI (`cloudctl`)**:
  - Unified commands: `init`, `install`, `start`, `stop`, `restart`, `status`, `doctor`, `update`, `backup`, `restore`, `migrate`, `uninstall`, `logs`, `security-check`, `test`, `bundle`.
  - Comprehensive host discovery (OS, kernel, CPU, RAM, disk, virtualization, runtimes, firewall).
  - Robust YAML configuration parser with JSON Schema validation and version migrations.
  - Safe secret management storing credentials securely outside source trees.
- **Container Runtime**:
  - Podman native pod manager with rootless support and resource limits.
  - Container manifests pinned to exact stable versions for Nextcloud, PostgreSQL, Redis, and Headscale.
  - Cross-platform orchestration support for Linux, Windows (WSL2/Podman Machine), and macOS.
- **Media Engine (`uspc-media`)**:
  - Dedicated asynchronous media streaming microservice with FastAPI and chunked file I/O.
  - Automatic filesystem scanner and indexing for video, audio, and image formats.
  - Metadata extraction (resolution, codec, duration, artist/album/title tags).
  - Dynamic thumbnail generation and caching for photos, video frame captures, and audio album art.
  - High-performance HTTP 206 Partial Content range request streaming engine with seeking support.
  - Transcoding engine for unsupported container formats.
- **Media Web Interface**:
  - Responsive Single-Page Application (SPA) with Grid and List views.
  - Integrated HTML5 video player with seek preview, playback speed, volume, and subtitle support.
  - Persistent background audio player with playlist management and metadata display.
  - Image lightbox viewer with zoom and EXIF inspection.
- **Networking & Security**:
  - WireGuard + self-hosted Headscale VPN orchestration for zero-exposure private remote access.
  - Automated security inspection engine (`cloudctl security-check`) evaluating ports, permissions, and TLS.
- **Backup & Disaster Recovery**:
  - AES-256 encrypted backups via Restic integration with integrity verification (`--verify`).
  - Disaster recovery and migration tooling with versioned portable migration bundles (`cloudctl migrate`).
- **Testing & Quality Assurance**:
  - Comprehensive unit, integration, media, security, and migration test suite targeting >90% coverage.
  - CI/CD workflow definitions for automated testing, linting, and security audits.
