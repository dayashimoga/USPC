# USPC Requirements

> Version 0.1.0 | Last verified: 2026-08-17

## 1. Functional Requirements

### 1.1 Cloud Platform
- **FR-01**: One-command bootstrap (`cloudctl setup`) that detects the host OS, installs dependencies, generates secrets, initializes storage, and deploys containers idempotently.
- **FR-02**: Nextcloud Community (27.1.4-apache) file sync and sharing with PostgreSQL 16 and Redis 7.2.
- **FR-03**: Declarative YAML configuration (`config/cloud.yaml`) with JSON Schema validation (`config/schema.yaml`).
- **FR-04**: 5-stage configuration precedence: AUTO → DEFAULT → PROFILE → ENVIRONMENT → USER-OVERRIDE.
- **FR-05**: Configuration migration across schema versions (0.1.0 → 0.2.0 → 0.3.0).

### 1.2 Media Service
- **FR-10**: FastAPI-based media streaming microservice on port 8085 (configurable).
- **FR-11**: Automatic filesystem scanner and indexer for video, audio, and image files.
- **FR-12**: HTTP 206 Partial Content range-request streaming with chunked I/O and seeking.
- **FR-13**: Dynamic thumbnail generation (photos, video frames, audio album art).
- **FR-14**: Background transcoding for unsupported container formats via FFmpeg.
- **FR-15**: Metadata extraction (resolution, codec, duration, artist, album, title).
- **FR-16**: HTML5 SPA web interface with video player, audio dock, and image lightbox.

### 1.3 Orchestration
- **FR-20**: Podman Appliance Mode as default (single-node, rootless Podman/Docker).
- **FR-21**: K3s Cluster Mode as optional (2+ nodes, declarative Kubernetes manifests in `deploy/k3s/`).
- **FR-22**: Switchable orchestration via `cloudctl orchestrator switch appliance|cluster`.
- **FR-23**: Common `Orchestrator` ABC with `PodmanBackend` and `K3sBackend` implementations.
- **FR-24**: Service scaling in cluster mode (`cloudctl orchestrator scale <service> <replicas>`).

### 1.4 Networking
- **FR-30**: Self-hosted Headscale VPN coordination server for WireGuard mesh networking.
- **FR-31**: Private network mode (default): no public port exposure; all traffic over VPN.
- **FR-32**: Public network mode (optional): HTTP/HTTPS reverse proxy with TLS.
- **FR-33**: Peer enrollment via `headscale nodes register`.

### 1.5 Backup & Disaster Recovery
- **FR-40**: Encrypted backups via Restic (AES-256, client-side encryption).
- **FR-41**: Backup creation (`cloudctl backup`), restore (`cloudctl restore`), and verification (`--verify`).
- **FR-42**: Automated retention pruning (daily/weekly/monthly).
- **FR-43**: Portable migration bundles (`cloudctl migrate export/import`).

### 1.6 Monitoring & Observability
- **FR-50**: Four monitoring profiles: MINIMAL, STANDARD, FULL, CLUSTER.
- **FR-51**: Prometheus-compatible `/metrics` endpoint with OpenTelemetry text format.
- **FR-52**: Live terminal dashboard (`cloudctl monitor`) with CPU, RAM, disk, streams.
- **FR-53**: Threshold-based alerts (`cloudctl alerts`) with lifecycle (TRIGGERED → FIRING → ACKNOWLEDGED → RESOLVED).
- **FR-54**: K3s manifests for Prometheus, Grafana, Loki, and Alertmanager.

### 1.7 Security
- **FR-60**: HMAC-SHA256 token-based authentication with constant-time verification.
- **FR-61**: Token revocation registry.
- **FR-62**: Path traversal protection on all file access endpoints.
- **FR-63**: Sliding-window per-IP rate limiting.
- **FR-64**: Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
- **FR-65**: Rootless container execution by default.
- **FR-66**: Secret vault with 0600 file permissions.

### 1.8 Supply Chain
- **FR-70**: SPDX 2.3 SBOM generation (`cloudctl sbom --format json`).
- **FR-71**: CycloneDX 1.5 SBOM generation (`cloudctl sbom --format cyclonedx`).
- **FR-72**: License compliance audit (`cloudctl sbom --audit`) — 100% FOSS.
- **FR-73**: SBOM drift detection (`cloudctl sbom --verify-drift`).

---

## 2. Non-Functional Requirements

### 2.1 Supported Platforms
| Platform | Container Runtime | Status |
|---|---|---|
| Linux (Ubuntu 22.04+, Debian 12+, Fedora 38+, Arch) | Podman (rootless) or Docker | **Fully Supported** |
| Windows 10/11 + WSL2 | Docker Desktop or Podman Machine | **Fully Supported** |
| macOS 13+ (Intel & Apple Silicon) | Podman Machine or Docker Desktop | **Fully Supported** |

### 2.2 Performance
- API response P95 latency < 100 ms.
- Media stream start P95 < 250 ms.
- Upload throughput ≥ 10 MB/s.
- Soak test RSS drift < 5 MB/hour.
- Hardware auto-tuning: TINY / SMALL / STANDARD / PERFORMANCE / MEDIA profiles.

### 2.3 Availability & Scalability
- Single-node appliance: no built-in HA (restart recovery).
- K3s cluster: rolling updates, node failure recovery, horizontal pod scaling.
- Max concurrent streams: auto-tuned from 2 (TINY) to 100 (MEDIA profile).

### 2.4 Security
- All secrets generated with cryptographically secure random generators (≥32 chars).
- Secrets directory: 0700; secrets file: 0600.
- No secrets committed to source control (Trufflehog CI scan).
- Bandit static analysis: 0 Medium/High issues required.

### 2.5 OSS / Vendor Independence
- 100% free and open-source software. Zero SaaS or proprietary dependencies.
- License: AGPL-3.0.
- All container images: pinned to stable open-source versions.

### 2.6 Acceptance Criteria
- ≥ 95% code coverage (`fail_under = 95` in pyproject.toml).
- 100% test pass rate with 0 skipped tests.
- 0 Ruff linter errors, 0 Bandit Medium/High issues.
- `cloudctl acceptance --full --strict` must exit 0 on all software gates.

### 2.7 Hardware-Dependent Requirements
These cannot be validated without physical hardware:
- Multi-device WAN mesh routing across distinct ISPs (HARDWARE-REQUIRED).
- Physical WireGuard tunnel latency measurement (HARDWARE-REQUIRED).

---

## Cross-References

- [Architecture](ARCHITECTURE.md) | [Implementation](../IMPLEMENTATION.md) | [Configuration](CONFIGURATION.md)
- [Security](../SECURITY.md) | [Networking](NETWORKING.md) | [Performance](PERFORMANCE.md)
- [Acceptance](ACCEPTANCE.md) | [Testing](TESTING.md) | [Project Status](../PROJECT_STATUS.md)
