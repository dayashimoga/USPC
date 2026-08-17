# USPC Configuration Reference (`config/cloud.yaml`)

USPC uses a single primary configuration file `config/cloud.yaml` with JSON Schema validation and automatic migration capabilities.

## Full Configuration Schema

```yaml
version: "0.1.0"

cloud:
  name: "mycloud"                       # Alphanumeric identifier (3-32 chars)
  environment: "production"             # production | development | testing
  domain: "mycloud.local"               # FQDN or local mesh hostname
  admin_user: "admin"                   # Primary administrator username
  admin_email: "admin@mycloud.local"    # Administrator email

runtime:
  engine: "auto"                        # auto | podman | docker
  rootless: true                        # Run containers in rootless mode
  vm_memory_mb: 4096                    # Allocated VM RAM on Windows/macOS
  vm_cpus: 2                            # Allocated VM CPU cores

storage:
  data_path: "~/.uspc/data"             # Persistent data location
  config_path: "~/.uspc/config"         # Runtime configuration location
  min_free_space_gb: 20                 # Enforce minimum free storage
  external_mounts: []                   # List of external drive mount points

performance:
  profile: "auto"                       # auto | tiny | small | standard | performance | media
  max_concurrent_streams: 15            # Maximum concurrent streams
  max_streams_per_user: 3               # Per-user stream limit
  max_transcode_concurrency: 2          # Maximum parallel video transcode jobs
  rate_limit_requests_per_minute: 600   # Sliding window request rate limit

network:
  mode: "private"                       # private (VPN-only) | public (Caddy + TLS)
  vpn_subnet: "100.64.0.0/10"           # WireGuard/Headscale CIDR subnet
  headscale_port: 8080                  # Headscale coordination port
  enable_magic_dns: true                # Enable MagicDNS inside VPN

services:
  nextcloud:
    version: "27.1.4-apache"            # Pinned Nextcloud release
    port: 8081                          # HTTP Port
  postgres:
    version: "16.1-alpine"              # Pinned PostgreSQL release
    port: 5432
    db_name: "nextcloud"
    user: "nextcloud"
  redis:
    version: "7.2-alpine"               # Pinned Redis release
    port: 6379

media:
  enabled: true                         # Enable FastAPI media microservice
  port: 8085                            # Media Web UI & Streaming Port
  thumbnail_width: 320                  # Grid thumbnail width (px)
  preview_width: 800                    # Lightbox preview width (px)
  chunk_size_kb: 64                     # HTTP 206 chunk buffer size (KB)
  background_processing: true           # Run indexing asynchronously

backup:
  enabled: true                         # Enable automated backups
  target_type: "local"                  # local | external | sftp
  target_path: "~/.uspc/backups"        # Backup destination
  retention_days: 30                    # Snapshot retention policy
  schedule: "0 2 * * *"                 # Daily cron backup schedule
  verify_after_backup: true             # Run cryptographic integrity check

security:
  enforce_mfa: false                    # Require TOTP 2FA
  auto_security_updates: true           # Automatic OS package security updates
  firewall_enabled: true                # Enforce host firewall isolation
  tls_enabled: false                    # TLS encryption for public access
```

---

## Configuration Management Commands

```bash
# Validate configuration against schema and semantic checks
cloudctl config validate

# View active overrides, defaults, and provenance with schema metadata
cloudctl config diff

# Export active configuration safely (secrets masked by default)
cloudctl config export [--unmask-secrets] [-o output.yaml]

# Import configuration atomically with automatic backup
cloudctl config import -i new_config.yaml

# Migrate configuration to a newer schema version
cloudctl config migrate [--target-version 0.3.0]
```

