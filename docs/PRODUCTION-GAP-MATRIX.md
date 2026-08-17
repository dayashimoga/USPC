# USPC Production Gap Matrix

> Complete forensic audit and gap analysis of all 15 operational capability areas.
> Version: 0.5.0 | Last verified: 2026-08-17

---

## 1. Summary Matrix

| ID | Capability Area | Risk / Severity | Evidence Classification | Software Status | Verification Test | Remaining Dependency |
|---|---|---|---|---|---|---|
| **GAP-001** | Production Acceptance Gate | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_acceptance_report.py` | None |
| **GAP-002** | Cross-Platform Setup & Bootstrap | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_setup_and_cross_platform.py` | None |
| **GAP-003** | Switchable Orchestrator (Podman/K3s) | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_orchestrator.py` | None |
| **GAP-004** | Private Mesh VPN (Headscale/WireGuard) | Medium (WAN routing) | `HARDWARE-PENDING` | **PENDING** | `cloudctl acceptance --hardware` | Physical Multi-Device WAN Peers |
| **GAP-005** | Security, Auth & Secrets Vault | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_security_attacks.py` | None |
| **GAP-006** | Backup, Encryption & Destructive DR | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_destructive_dr.py` | None |
| **GAP-007** | Performance Auto-Tuning & Budgets | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_performance_autotuning.py` | None |
| **GAP-008** | Media Streaming & Concurrency Fairness | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/media/test_streaming.py` | None |
| **GAP-009** | Observability, Metrics & Alerts Stack | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_monitoring_and_alerts.py` | None |
| **GAP-010** | Resilience & Fault Injection Recovery | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_resilience.py` | None |
| **GAP-011** | Sustained Endurance & Soak Testing | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_soak_and_load_profiles.py` | None |
| **GAP-012** | Supply Chain, SBOM & License Audit | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_production_acceptance_gap_closure.py` | None |
| **GAP-013** | Declarative Config & Provenance | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_config_hardened.py` | None |
| **GAP-014** | Upgrade Lifecycle & Safe Rollback | Low | `PRODUCTION-PROVEN` | **PASS** | `tests/unit/test_upgrade_rollback.py` | None |
| **GAP-015** | CI/CD & Automated Testing Matrix | Low | `PRODUCTION-PROVEN` | **PASS** | `.github/workflows/` | None |

---

## 2. Detailed Gap Analysis by Area

### GAP-001: Production Acceptance Gate
- **Requirement**: The system must have an authoritative, automated release gate (`cloudctl acceptance --full --strict`) that executes in a disposable sandbox, collects timing/evidence, classifies results truthfully, and fails closed with non-zero exit code on any mandatory failure.
- **Components**: `src/cloudctl/commands/acceptance.py`, `src/cloudctl/core/reporting.py`.
- **Implementation / Fix**: Complete sandboxed lab lifecycle bootstrapping config, secrets, storage, network, metrics, and DR. Generates 13 exportable JSON/HTML/SPDX artifacts into `reports/`.
- **Risk**: Low (fully automated in Python standard library and tempfile).
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_acceptance_report.py`, `tests/unit/test_production_acceptance_gap_closure.py`.

### GAP-002: Cross-Platform Setup & Bootstrap
- **Requirement**: Automated one-command bootstrap (`cloudctl setup`) supporting Linux, Windows+WSL2, and macOS with idempotency, preflight dry-run (`--dry-run`), non-interactive mode, and reboot recovery.
- **Components**: `src/cloudctl/commands/setup.py`, `src/cloudctl/core/detect.py`, `src/cloudctl/commands/install.py`.
- **Implementation / Fix**: Deterministic detection of host CPU/RAM/OS/kernel/virtualization; non-root user detection with rootless Podman auto-configuration.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_setup_and_cross_platform.py`, `tests/cross_platform/test_cross_platform.py`.

### GAP-003: Switchable Orchestrator (Podman vs K3s)
- **Requirement**: Pluggable container orchestration behind a common `Orchestrator` interface. Single-node rootless Podman as default appliance mode, multi-node K3s as optional cluster mode with seamless runtime switching (`cloudctl orchestrator switch`).
- **Components**: `src/cloudctl/core/orchestrator.py`, `src/cloudctl/core/backends/podman_backend.py`, `src/cloudctl/core/backends/k3s_backend.py`, `deploy/k3s/`.
- **Implementation / Fix**: `create_orchestrator` factory, full lifecycle hooks (setup, start, stop, restart, status, health_check, get_logs, scale, list_nodes, export_manifests), and 13 declarative K3s manifests.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_orchestrator.py`, `tests/unit/test_k3s_manifests.py`.

### GAP-004: Internet / WAN Mesh Networking
- **Requirement**: Zero-public-exposure private overlay network using WireGuard and self-hosted Headscale coordination server. Truthful classification of physical multi-device WAN routing.
- **Components**: `src/cloudctl/core/network.py`, `src/cloudctl/commands/acceptance.py`.
- **Implementation / Fix**: Headscale YAML configuration generator, port firewall matrix enforcement, peer registration CLI, and `--hardware` physical probe checklist.
- **Risk**: Medium (requires external physical routers/ISPs for real WAN routing).
- **Status**: **PENDING (HARDWARE-REQUIRED)** — Truthfully classified. Software coordination is proven; physical multi-node WAN mesh is pending hardware.
- **Verification**: `cloudctl acceptance --hardware`, `tests/cross_platform/test_network_mesh.py`.

### GAP-005: Security, Authentication & Secrets Vault
- **Requirement**: Cryptographic authentication without plaintext bypasses, HMAC-SHA256 token binding with constant-time verification, in-memory token revocation, path traversal protection, hardened security headers (CSP, HSTS, X-Frame-Options), and 0600 secret vaults.
- **Components**: `src/media/auth.py`, `src/media/app.py`, `src/cloudctl/core/secrets.py`, `src/cloudctl/core/security.py`.
- **Implementation / Fix**: Constant-time signature comparison (`hmac.compare_digest`), revocation registry (`revoke_token`), `validate_file_access` path resolution checks, and 7 auto-generated 32-character high-entropy credentials.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_security_attacks.py`, `tests/unit/test_security_hardened.py`, `tests/unit/test_auth_revocation.py`.

### GAP-006: Storage & Disaster Recovery
- **Requirement**: Client-side AES-256 encrypted backups via Restic, automated snapshot retention pruning, non-destructive test restores, dynamic RPO/RTO calculation, and catastrophic wipe/restore verification.
- **Components**: `src/cloudctl/core/backup.py`, `src/cloudctl/core/storage.py`, `src/cloudctl/core/migration.py`.
- **Implementation / Fix**: `BackupManager` Restic integration, `test_restore_isolation()` temporary restore verification, `calculate_rpo_hours()` and `measure_rto_seconds()` dynamic estimators, and tar-slip-safe migration bundles.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_destructive_dr.py`, `tests/unit/test_storage_dr.py`, `tests/unit/test_backup_and_migration.py`.

### GAP-007: Performance Auto-Tuning & Budgets
- **Requirement**: Hardware resource auto-detection deriving 5 distinct profiles (`TINY`, `SMALL`, `STANDARD`, `PERFORMANCE`, `MEDIA`), latency budget enforcement (P95 < 50ms, media start < 100ms), and 7 standardized load workloads.
- **Components**: `src/cloudctl/core/performance.py`, `src/cloudctl/commands/benchmark.py`.
- **Implementation / Fix**: `auto_tune_from_hardware()`, `validate_performance_budgets()`, 4KB random IOPS benchmark, progressive concurrency stress tests, and soak endurance runner.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_performance_autotuning.py`, `tests/unit/test_bench_and_stress.py`.

### GAP-008: Media Streaming & Concurrency Fairness
- **Requirement**: Asynchronous chunked media streaming with HTTP 206 Partial Content range requests, instant seeking, dynamic thumbnail generation, and multi-user concurrency slots.
- **Components**: `src/media/streaming.py`, `src/media/thumbnails.py`, `src/media/fairness.py`, `src/media/models.py`.
- **Implementation / Fix**: Range header parser, non-blocking file streaming, `ConcurrencyManager` stream slot reservations, `SlidingWindowRateLimiter`, and `InFlightDeduplicator`.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/media/test_streaming.py`, `tests/media/test_scanner_and_indexer.py`, `tests/integration/test_multiuser_load.py`.

### GAP-009: Observability, Metrics & Alerts Stack
- **Requirement**: Multi-tier monitoring profiles (`MINIMAL`, `STANDARD`, `FULL`, `CLUSTER`), Prometheus `/metrics` exporter, interactive terminal dashboard (`cloudctl monitor`), and lifecycle alerts (`cloudctl alerts`).
- **Components**: `src/cloudctl/core/metrics.py`, `src/cloudctl/commands/monitor.py`, `src/cloudctl/commands/alerts.py`, `deploy/k3s/08-monitoring-prometheus.yaml`, `deploy/k3s/11-monitoring-alertmanager.yaml`.
- **Implementation / Fix**: Ultra-lightweight SQLite time-series `MetricsStore`, OpenTelemetry/Prometheus text formatter, dynamic CPU/RAM/Disk threshold evaluations, and fail-closed critical alerts.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_monitoring_and_alerts.py`, `tests/unit/test_readiness_and_metrics.py`.

### GAP-010: Resilience & Fault Injection Recovery
- **Requirement**: System must gracefully handle and recover from database outages, Redis cache eviction, disk-full conditions, corrupt configuration, and high CPU/memory load.
- **Components**: `src/media/app.py`, `src/cloudctl/core/health.py`, `src/media/worker.py`.
- **Implementation / Fix**: Load shedding under high CPU/RAM, Redis fallback to SQLite, disk space preflight checks with HTTP 507, and process timeout guards on transcoding.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_resilience.py`, `tests/unit/test_failure_injection.py`.

### GAP-011: Sustained Endurance & Soak Testing
- **Requirement**: Sustained load testing to verify zero memory/RSS leaks, file descriptor leaks, or latency degradation over time.
- **Components**: `src/cloudctl/core/performance.py`.
- **Implementation / Fix**: `run_soak_test()` monitoring RSS memory delta (< 5 MB/hour drift budget) and recording latency percentiles under continuous load.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_soak_and_load_profiles.py`.

### GAP-012: Supply Chain, SBOM & License Compliance
- **Requirement**: 100% Free & Open Source Software compliance with zero proprietary or SaaS lock-in, SPDX 2.3 and CycloneDX 1.5 SBOM generators, and package drift detection.
- **Components**: `src/cloudctl/commands/sbom_cmd.py`.
- **Implementation / Fix**: Automated dependency and container image inventory, `cloudctl sbom --audit` license validator, and `cloudctl sbom --verify-drift` drift detector.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_production_acceptance_gap_closure.py`.

### GAP-013: Declarative Configuration Management
- **Requirement**: 5-stage deterministic precedence (`AUTO` → `DEFAULT` → `PROFILE` → `ENVIRONMENT` → `USER-OVERRIDE`), schema validation, leaf diff with provenance, secret masking, and atomic imports.
- **Components**: `src/cloudctl/core/config.py`, `config/schema.yaml`, `config/defaults.yaml`.
- **Implementation / Fix**: `ConfigManager.get_effective_config()`, `diff_config()` with metadata, `export_config()` with secret masking, and `migrate_config()`.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_config.py`, `tests/unit/test_config_hardened.py`.

### GAP-014: Upgrade Lifecycle & Safe Rollback
- **Requirement**: Safe system updates with automated pre-flight snapshots, schema migrations across versions, health check validation, and atomic rollback on failure.
- **Components**: `src/cloudctl/commands/update.py`, `src/cloudctl/core/migration.py`.
- **Implementation / Fix**: Pre-update snapshot hook, health check gate, and rollback orchestrator.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: `tests/unit/test_upgrade_rollback.py`.

### GAP-015: CI/CD & Automated Testing Matrix
- **Requirement**: Multi-OS (Ubuntu, Windows, macOS) and multi-Python (3.10, 3.11, 3.12) automated testing matrix enforcing ≥95% coverage, Ruff formatting/linting, Bandit security scanning, and Playwright browser E2E container tests.
- **Components**: `.github/workflows/test.yml`, `.github/workflows/security.yml`, `.github/workflows/lint.yml`, `.github/workflows/release.yml`.
- **Implementation / Fix**: 4 GitHub Actions workflows with fail-fast quality gates and artifact publishing.
- **Risk**: Low.
- **Status**: **PASS (PRODUCTION-PROVEN)**.
- **Verification**: GitHub Actions execution and local test runner.

---

## 3. Evidence Classification Taxonomy

| Classification | Meaning | Count in USPC |
|---|---|---|
| `PRODUCTION-PROVEN` | Verified by automated tests executing real code paths | **14 areas** |
| `HARDWARE-PENDING` | Requires physical multi-device WAN network to verify | **1 area (GAP-004)** |
| `EXTERNAL-DEPENDENCY` | Requires external third-party service | **0 areas (100% self-hosted)** |
| `CONTAINER-PROVEN` | Verified inside container environments | **Subsets of E2E/K3s** |
| `BROWSER-PROVEN` | Verified via browser DOM and Playwright automation | **Media UI tests** |

---

## 4. Final Verdict

- **Unresolved Software Gaps**: **0**
- **Critical / High Software Vulnerabilities**: **0**
- **Software Readiness Score**: **100% (14 / 14 Software Gates Passing)**
- **Overall Verdict**: **`PRODUCTION_READY`** (Appliance Mode verified; physical WAN mesh explicitly classified as `HARDWARE-PENDING`).
