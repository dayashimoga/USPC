# Changelog

All notable changes to the Universal Personal Cloud Platform (USPC) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-17
### 100% Production-Ready Acceptance, Monitoring Profiles, CycloneDX SBOM & Security Modernization
- **Modern Security Headers & CSP Modernization**:
  - Removed deprecated `X-XSS-Protection` header.
  - Implemented strict Content Security Policy (`frame-ancestors 'none'`, explicit script/style/media origins), Permissions-Policy, HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and API cache-control directives.
- **Observability Stack & Monitoring Profiles (`MINIMAL`, `STANDARD`, `FULL`, `CLUSTER`)**:
  - Added declarative Kubernetes manifests for Prometheus, Grafana, and Loki in `deploy/k3s/` (`08-monitoring-prometheus.yaml`, `09-monitoring-grafana.yaml`, `10-monitoring-loki.yaml`).
  - Added multi-tier monitoring profiles (`--profile minimal|standard|full|cluster`).
  - Extended `MetricSnapshot` and Prometheus exporter with Disk IO (`uspc_io_read_megabytes`, `uspc_io_write_megabytes`), Network egress/ingress (`uspc_net_sent_megabytes`, `uspc_net_recv_megabytes`), and P95 response latency (`uspc_latency_p95_ms`).
- **CycloneDX 1.5 & Automated License Auditing**:
  - Added CycloneDX 1.5 JSON export in `cloudctl sbom --format cyclonedx`.
  - Added automated open-source license compliance audit (`cloudctl sbom --audit`) validating 0% SaaS / proprietary lock-in.
  - Added container images and binary packages to certified open-source inventory.
- **Hardware Performance Auto-Tuning & Budget Validation**:
  - Added `auto_tune_from_hardware()` automatically sizing memory limits, database connection pools, concurrency slots, and transcoder workers based on host resources.
  - Added `validate_performance_budgets()` and acceptance gates for P50/P95/P99 latency, startup time, and upload throughput.
  - Enforced deterministic 5-stage configuration precedence: `AUTO -> DEFAULT -> PROFILE -> ENVIRONMENT -> USER-OVERRIDE`.
- **Enhanced 14-Gate Acceptance Framework & 16 Production Reports**:
  - Upgraded `cloudctl acceptance --full --strict` as the authoritative release gate exporting all 16 JSON, HTML, and SPDX/CycloneDX audit reports.
- **Repository-Wide Documentation Suite & Consistency Enforcement**:
  - Complete rewrite and verification of 25 documentation files across architecture, operations, compliance, and user guides.
  - Automated continuous documentation consistency suite (`tests/unit/test_documentation_consistency.py`) validating commands, configs, and internal links.
- **Quality & Test Scale**:
  - Expanded test suite to **226 automated tests** with **100% pass rate (0 skips)** and **95.66% code coverage**.
  - 0 Ruff lint/format errors, 0 Bandit security vulnerabilities.

## [0.4.0] - 2026-08-17

### Switchable Orchestrator, Observability Stack & Production Acceptance Lab
- **Switchable Orchestrator Abstraction (`PodmanBackend` vs `K3sBackend`)**:
  - Implemented `Orchestrator` abstract base interface and factory (`create_orchestrator`).
  - Added `PodmanBackend` for single-node Appliance Mode (default for Linux, macOS, and Windows+WSL2) with rootless Podman/Docker.
  - Added `K3sBackend` for multi-node Cluster Mode (2+ servers) with rolling updates, node inspection, and declarative K3s Kubernetes manifests (`deploy/k3s/`).
  - Added `cloudctl orchestrator status|switch|nodes|scale|manifests` CLI command suite for seamless, zero-downtime runtime switching.
- **100% Free & Open-Source Vendor-Neutral Observability**:
  - Added standardized Prometheus / OpenTelemetry text format exporter on `/metrics` endpoint with latency tracking and active stream metrics.
  - Implemented `cloudctl monitor` providing a live interactive terminal monitoring dashboard with CPU, RAM, disk, stream slots, queue depths, and bottleneck detection.
  - Implemented `cloudctl alerts` for proactive threshold alerts with fail-closed exit codes for critical alerts.
  - Implemented `cloudctl sbom` generating SPDX 2.3 Software Bill of Materials and auditing open-source license compliance (0% SaaS lock-in).
- **Performance Budgets & Low-Latency Streaming**:
  - Enforced strict performance budgets (P95 latency < 50ms, media startup < 100ms, upload throughput >= 10MB/s).
  - Added HTTP 416 Range Not Satisfiable handling with compliant `Content-Range: bytes */total` headers.
  - Standardized response security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection`, `X-Process-Time-Ms`).
  - Added structured security audit logging for authentication and authorization events.
- **Automated Production-Acceptance Lab (`cloudctl acceptance --full`)**:
  - 12 formal acceptance gates executing in a clean disposable sandbox.
  - Automatically generates machine-readable `acceptance.json` and standalone interactive `acceptance.html` dashboard.
- **7-Layer Production Readiness Audit**:
  - Structured `cloudctl readiness` into 7 explicit evaluation layers: Infrastructure, Orchestration, Application, Security, Storage & Recovery, Observability, and External-Remote.
- **Test Suite Scale & Coverage**:
  - Expanded test suite to **202 automated tests** passing at **100%** with **95.74% overall code coverage**.
  - 0 Ruff lint/format errors, 0 Bandit security vulnerabilities.



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
