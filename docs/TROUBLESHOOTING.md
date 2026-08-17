# USPC Troubleshooting

## Installation & Setup

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| `cloudctl: command not found` | Not installed or not in PATH | `pip install -e ".[dev]"` or use `python -m cloudctl.cli` | `cloudctl --version` |
| "Configuration file not found" | Missing `config/cloud.yaml` | Run `cloudctl init` or `cloudctl setup` | `cloudctl config validate` |
| "Configuration error at [...]" | Schema validation failure | Check error message, fix `cloud.yaml` against `config/schema.yaml` | `cloudctl config validate` |
| Setup fails on Windows | Missing WSL2 or Docker | Install WSL2 + Docker Desktop | `wsl --version`, `docker --version` |

## Networking

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| Cannot reach Nextcloud remotely | VPN not connected | Install WireGuard, connect via Headscale | `ping <vpn-ip>` |
| Headscale port unreachable | Firewall blocking 8080 | Open port 8080/TCP | `telnet <host> 8080` |
| DNS resolution fails | MagicDNS not configured | Check `network.enable_magic_dns` | `cloudctl doctor` |
| High latency via VPN | Using DERP relay | Check direct WireGuard connection | `wg show` |

## Authentication

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| "401 Authentication required" | Missing/expired/revoked token | Generate new token or use Bearer header | Check token expiry |
| "403 Path traversal detected" | Security protection triggered | Use valid file paths within data directory | — |
| Rate limited (429) | Too many requests per minute | Wait, or increase `performance.rate_limit_requests_per_minute` | `cloudctl config diff` |

## Storage & Media

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| Upload fails | Disk full or file too large | Check `storage.min_free_space_gb`, run `cloudctl cleanup` | `cloudctl performance` |
| Thumbnails missing | FFmpeg/Pillow not available | Install FFmpeg and Pillow | `ffmpeg -version` |
| Media not appearing | Index not synced | `curl http://localhost:8085/api/scan` | Check media database |
| Transcoding fails | FFmpeg timeout or crash | Check logs, increase `media.max_transcode_jobs` | `cloudctl logs -s media` |

## Database & Cache

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| PostgreSQL connection refused | Container not running | `cloudctl start` | `cloudctl status` |
| Redis connection refused | Container not running | `cloudctl start` | `cloudctl status` |
| Slow queries | Connection pool exhausted | Increase `performance.db_connection_pool_size` | `cloudctl performance` |

## Monitoring

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| No metrics data | Monitoring disabled | Set `monitoring.enabled: true` | `cloudctl monitor` |
| Prometheus endpoint empty | Wrong profile | Set `monitoring.profile: standard` or higher | `curl localhost:8085/metrics` |
| Alert not firing | Threshold too high | Adjust `monitoring.alert_*_threshold` | `cloudctl alerts` |

## Backup & Restore

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| "Restic CLI not available" | Restic not installed | Install: `apt install restic` / `brew install restic` | `restic version` |
| Backup fails | Disk full | Free space or change `backup.target_path` | `df -h` |
| Restore integrity error | Corrupted repository | Run `cloudctl backup --verify` | Check Restic output |

## Podman / Docker

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| "Cannot connect to container runtime" | Engine not running | Start Docker/Podman daemon | `docker info` or `podman info` |
| Container OOMKilled | Insufficient memory | Increase `runtime.vm_memory_mb` | `cloudctl doctor` |
| Rootless mode fails | User namespace not configured | Enable user namespaces: `sysctl user.max_user_namespaces=28633` | `podman info` |

## K3s Cluster

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| "K3s not available" | K3s not installed | Install K3s: `curl -sfL https://get.k3s.io \| sh -` | `k3s --version` |
| Pods not scheduling | Node not ready | Check `kubectl get nodes` | `cloudctl orchestrator nodes` |
| Manifests not applying | Kustomize error | Check YAML syntax in `deploy/k3s/` | `kubectl apply -k deploy/k3s/ --dry-run=client` |

## Performance

| Symptom | Diagnosis | Fix | Verification |
|---|---|---|---|
| High CPU usage | Transcoding or indexing | Reduce `media.max_transcode_jobs` | `cloudctl monitor` |
| High memory usage | Too many concurrent streams | Reduce `performance.max_concurrent_streams` | `cloudctl performance` |
| Slow streaming | Large chunk size or disk IO | Adjust `media.chunk_size_kb` | `cloudctl benchmark` |

---

## General Diagnostic Commands

```bash
cloudctl doctor --fix     # Auto-remediate detected issues
cloudctl status --json    # Machine-readable service status
cloudctl readiness --json # Full readiness audit
cloudctl logs --follow    # Live log stream
cloudctl performance      # Current resource usage
cloudctl security-check   # Security audit
```

---

## Cross-References

- [CLI Reference](CLI-REFERENCE.md) | [Configuration](CONFIGURATION.md) | [Monitoring](MONITORING.md)
- [Setup Guides](setup/) | [Networking](NETWORKING.md) | [Backup & DR](BACKUP-DR.md)
