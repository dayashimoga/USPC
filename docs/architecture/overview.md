# USPC Technical Architecture Overview

The Universal Personal Cloud Platform (USPC) converts any Linux, Windows, or macOS host into a secure, vendor-independent personal cloud with integrated media streaming, encrypted backups, and private mesh networking.

## Architectural Principles

1. **Vendor-Independent & 100% Free/Open-Source**: No proprietary cloud APIs, SaaS dependencies, or mandatory subscriptions.
2. **Private-First Overlay Mesh**: Default zero public exposure via WireGuard + self-hosted Headscale.
3. **Container-Native Runtime**: Podman as primary rootless engine with Docker compatibility.
4. **Adaptive Multi-User Performance**: Automatic hardware capacity detection and resource profile selection (`TINY`, `SMALL`, `STANDARD`, `PERFORMANCE`, `MEDIA`).
5. **Non-Blocking Streaming Layer**: FastAPI asynchronous microservice with HTTP 206 Partial Content range requests, chunked file I/O, and in-flight deduplication.

---

## System Component Diagram

```mermaid
graph TB
    subgraph ClientLayer["Clients & User Access"]
        WebBrowser["Modern Web UI / SPA"]
        MobileApp["Nextcloud Mobile Client"]
        DesktopApp["Nextcloud Desktop Sync"]
        VPNClient["WireGuard / Tailscale Client"]
    end

    subgraph NetworkMesh["Private Mesh Network (100.64.0.0/10)"]
        Headscale["Headscale VPN Coordinator (:8080)"]
        WireGuardTunnel["Encrypted WireGuard Mesh Tunnel"]
    end

    subgraph HostRuntime["Host System (Linux / Windows WSL2 / macOS)"]
        subgraph PodmanPod["USPC Pod (Isolated Container Network)"]
            Nextcloud["Nextcloud Community 27.x (:8081)<br/>(File Engine, WebDAV, Auth)"]
            MediaService["USPC Media Service (:8085)<br/>(FastAPI, Async Streaming, Indexer)"]
            Postgres["PostgreSQL 16.x (:5432)<br/>(Metadata, File Database)"]
            Redis["Redis 7.2.x (:6379)<br/>(Memory Cache, Locks)"]
        end

        subgraph PersistentStorage["Persistent Storage Tiers"]
            SSD_Tier["High-Speed SSD / NVMe Tier<br/>(PostgreSQL DB, Redis, Media Index SQLite, Thumbnail Cache)"]
            Bulk_Tier["Bulk Storage Tier (SSD/HDD/USB/NAS)<br/>(Nextcloud User Files, 4K Videos, FLAC Audio)"]
            Backup_Tier["Encrypted Backup Target<br/>(Restic AES-256 Snapshots)"]
        end
    end

    ClientLayer --> WireGuardTunnel
    WireGuardTunnel --> Headscale
    WireGuardTunnel --> Nextcloud
    WireGuardTunnel --> MediaService

    Nextcloud --> Postgres
    Nextcloud --> Redis
    Nextcloud --> Bulk_Tier

    MediaService --> SSD_Tier
    MediaService --> Bulk_Tier

    HostRuntime -.-> Backup_Tier
```

---

## Media Streaming & HTTP 206 Range Request Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser / Client
    participant API as USPC Media API (FastAPI)
    participant Fairness as Fairness & Concurrency Manager
    participant Cache as SSD Thumbnail & Meta Cache
    participant Disk as Storage (Bulk Data)

    User->>API: GET /api/media (Browse Library)
    API->>Cache: Query SQLite Media Database
    Cache-->>API: Return Paginated Items & Tokens
    API-->>User: Render Fluid Responsive Grid

    User->>API: Click Thumbnail (GET /api/media/{id}/stream with Range: bytes=0-1048575)
    API->>Fairness: Acquire Stream Slot (Check Concurrency Limits)
    Fairness-->>API: Slot Approved

    API->>Disk: Async Read Chunk (64 KB buffers)
    Disk-->>API: Stream Binary Bytes
    API-->>User: HTTP 206 Partial Content (Content-Range: bytes 0-1048575/Total)

    Note over User,API: User seeks to 50% duration (instant scrub)
    User->>API: GET /api/media/{id}/stream with Range: bytes=52428800-53477375
    API->>Disk: Async Seek & Stream Target Chunk
    Disk-->>API: Stream Target Bytes
    API-->>User: HTTP 206 Partial Content (Immediate Playback)

    User->>API: Close Player / Tab
    API->>Fairness: Release Stream Slot
```

---

## Hardware Resource Profiles Matrix

| Profile | Target Hardware | Max Streams | Max Per User | Max Transcode Jobs | DB Pool Size | Redis RAM | Rate Limit (RPM) |
|---|---|---|---|---|---|---|---|
| **TINY** | < 2GB RAM, 1 CPU Core | 2 | 1 | 0 (Direct stream only) | 5 | 128 MB | 120 |
| **SMALL** | 2 - 4GB RAM, 2 CPU Cores | 5 | 2 | 1 | 10 | 256 MB | 300 |
| **STANDARD** | 4 - 8GB RAM, 4 CPU Cores | 15 | 3 | 2 | 25 | 512 MB | 600 |
| **PERFORMANCE** | 8 - 16GB RAM, 6+ Cores | 40 | 5 | 4 | 50 | 1024 MB | 1200 |
| **MEDIA** | 16GB+ RAM, 8+ Cores, NVMe | 100 | 10 | 8 | 100 | 2048 MB | 2400 |
