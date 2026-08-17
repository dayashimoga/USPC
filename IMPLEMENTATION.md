# Architectural Decisions & Implementation Log

This document records the architectural context, design decisions (ADRs), and rationale behind the Universal Personal Cloud Platform (USPC).

## Architectural Decision Records (ADRs)

### ADR 001: 100% Free & Open-Source, Vendor-Independent Foundation
- **Status**: Accepted
- **Context**: Users require a personal cloud platform free from SaaS dependencies (e.g. AWS, Cloudflare, proprietary identity providers).
- **Decision**: All components are 100% open source. Cloud storage uses Nextcloud Community, database uses PostgreSQL, cache uses Redis, VPN uses WireGuard + Headscale, and backup uses Restic.
- **Consequences**: Zero vendor lock-in, fully reproducible, self-contained.

### ADR 002: Dedicated FastAPI Media Streaming Microservice (`uspc-media`)
- **Status**: Accepted
- **Context**: Standard Nextcloud media plugins often fail to support robust HTTP 206 Range requests for huge files, smooth seeking without full buffer download, audio background playlists, or fast asynchronous thumbnail generation without web UI lag.
- **Decision**: Deploy a dedicated lightweight Python (FastAPI + uvicorn + Pillow + FFmpeg) microservice sharing Nextcloud's persistent storage volume read-only.
- **Consequences**: Fast asynchronous media scanning, chunked non-blocking Range streaming, instant seek without memory saturation, custom web client with integrated HTML5 player, while keeping Nextcloud as the authoritative storage layer.

### ADR 003: Private-First Networking via WireGuard & Headscale
- **Status**: Accepted
- **Context**: Exposing home/personal servers directly to public IPv4/IPv6 creates severe attack surfaces.
- **Decision**: Default to private VPN mesh overlay using Headscale (open-source Tailscale control server) and WireGuard. Optional public mode with Caddy reverse proxy requires explicit user confirmation.
- **Consequences**: Maximum privacy and security; no public ports required.

### ADR 004: Podman as Primary Container Engine
- **Status**: Accepted
- **Context**: Docker Desktop requires commercial licensing for enterprise users and has heavier resource overhead.
- **Decision**: Use Podman OCI engine natively on Linux, and via WSL2/Podman Machine on Windows and macOS.
- **Consequences**: Rootless operation by default, daemonless execution, systemd integration.

### ADR 005: Encrypted Off-site & On-site Backups with Restic
- **Status**: Accepted
- **Context**: Data integrity and disaster recovery are essential for personal clouds.
- **Decision**: Integrate Restic for client-side encrypted, deduplicated, snapshot-based backups of PostgreSQL dumps, Nextcloud data, and configuration metadata.
- **Consequences**: Secure backups to any local disk, NAS, or SFTP server with automated verification (`--verify`).

### ADR 006: Version Pinning & Zero Placeholders
- **Status**: Accepted
- **Context**: `latest` container tags cause unexpected breakage and reproducibility failures.
- **Decision**: Pin exact container versions (e.g. Nextcloud 27.1.4, Postgres 16.1, Redis 7.2, Headscale 0.22.3) and avoid dummy/mock implementations in production code paths.
- **Consequences**: Rock-solid reproducibility across deployments and migrations.

### ADR 007: Production Readiness Assessment & Compliance Engine (`cloudctl readiness`)
- **Status**: Accepted
- **Context**: Administrators need an authoritative command to assess if an instance is genuinely ready for production workloads.
- **Decision**: Implement `cloudctl readiness` evaluating container engine responsiveness, individual service health, storage IOPS/latency, security audits, encrypted backup status, and recent metric anomalies. Generates clear `PRODUCTION_READY`, `READY`, `DEGRADED`, or `NOT_READY` verdicts with automated blocker identification.
- **Consequences**: Deterministic, automated validation of deployment readiness without manual inspection.

### ADR 008: Self-Contained Historical Metrics & Proactive Alerting
- **Status**: Accepted
- **Context**: Heavy observability stacks (Prometheus/Grafana) consume excessive resources on small personal clouds.
- **Decision**: Deploy an ultra-lightweight SQLite time-series metric store capturing timestamped resource utilization, active streams, and queue depths with automated 30-day compaction and threshold alerts.
- **Consequences**: Zero SaaS dependencies, zero external agents, proactive alerting with negligible CPU/RAM overhead.

### ADR 009: Strict HMAC Token Binding & Revocation Registry
- **Status**: Accepted
- **Context**: Media tokens must prevent IDOR attacks, cross-item reuse, and provide instant revocation upon session termination.
- **Decision**: Eliminate raw secret query parameters completely. Enforce 3-part cryptographic tokens (`user_id:expiry:signature`) bound to specific item IDs, backed by an in-memory revocation registry.
- **Consequences**: Complete protection against IDOR, URL sniffing, and replay vulnerabilities.

### ADR 010: Declarative Configuration Management & Provenance Tracking
- **Status**: Accepted
- **Context**: Users need visibility into which settings are auto-detected hardware defaults vs explicit user overrides.
- **Decision**: Provide `cloudctl config validate|diff|export|import` with leaf-level provenance tracking (`AUTO`, `DEFAULT`, `USER-OVERRIDE`) and automated secret masking.
- **Consequences**: Fully transparent configuration drift detection and seamless configuration portability.

### ADR 011: 5-Layer Readiness Audit & Bounded Metric Observability
- **Status**: Accepted
- **Context**: Production readiness cannot treat all subsystems as a flat list; failures in core runtime differ from degraded secondary caches or metric alerts.
- **Decision**: Structure `cloudctl readiness` into 5 explicit evaluation layers: Infrastructure, Application, Security, Recovery, and Observability. Enforce a 100MB bounded storage ceiling on SQLite metrics with automated pruning and VACUUM compaction.
- **Consequences**: Clear, categorized failure identification without risking host disk saturation.

### ADR 012: Empirical Capability Classification & Truthful Verification Gates
- **Status**: Accepted
- **Context**: Claiming features are "PROVEN" without matching empirical evidence creates false security and reliability guarantees.
- **Decision**: Adopt a strict 8-tier classification taxonomy (`UNIT-PROVEN`, `INTEGRATION-PROVEN`, `CONTAINER-PROVEN`, `VM-PROVEN`, `REAL-NETWORK-PROVEN`, `BROWSER-PROVEN`, `HARDWARE-REQUIRED`, `NOT-TESTED`). Package Playwright browser tests and mesh networking suites into containerized harnesses.
- **Consequences**: Full transparency regarding verified vs simulated vs hardware-dependent platform capabilities.

### ADR 013: Switchable Orchestrator Abstraction (Podman Appliance vs K3s Cluster)
- **Status**: Accepted
- **Context**: Users running a single personal laptop or home server need lightweight, zero-overhead rootless Podman/Docker (Appliance Mode), while multi-server deployments (2+ nodes) require Kubernetes container scheduling, rolling updates, and horizontal scaling (Cluster Mode).
- **Decision**: Establish an `Orchestrator` base interface with `PodmanBackend` (Appliance Mode, default) and `K3sBackend` (Cluster Mode, declarative manifests). Users switch modes declaratively in `config/defaults.yaml` via `orchestrator.mode: appliance | cluster` or via `cloudctl orchestrator switch <mode>`.
- **Consequences**: Zero architectural rewriting required when scaling from a single laptop to a multi-node K3s cluster. Complete data portability with shared PVC volume models.

### ADR 014: 100% Free & Open-Source Vendor-Neutral Observability with Prometheus Text Format
- **Status**: Accepted
- **Context**: Operational monitoring must remain 100% self-hosted with zero SaaS subscriptions, zero proprietary telemetry agents, and zero third-party cloud lock-in.
- **Decision**: Expose OpenTelemetry and Prometheus-compatible metrics on `/metrics` endpoint and via `cloudctl metrics|monitor|alerts` using a bounded, self-compacting local SQLite time-series store (<100MB ceiling with automatic rolling retention).
- **Consequences**: Zero telemetry data leakage, fully functional in offline/LAN environments, native compatibility with standard Prometheus/Grafana or terminal CLI dashboards.

### ADR 015: Configurable Performance Budgets & Low-Latency Range Streaming
- **Status**: Accepted
- **Context**: Media streaming and API responses must maintain low latency and deterministic response times without high CPU/RAM overhead or memory leaks.
- **Decision**: Enforce strict performance budgets (P95 API latency < 50ms, media startup < 100ms, upload throughput >= 10MB/s) combined with chunked HTTP 206 Byte-Range streaming, 416 Range Not Satisfiable validation, response header injection (`X-Process-Time-Ms`, security headers), and adaptive concurrency slots.
- **Consequences**: Deterministic responsiveness across low-end and high-performance hardware with graceful degradation under resource pressure.


