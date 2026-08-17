# USPC CLI Reference

> `cloudctl` — Universal Personal Cloud Platform Control Tool
> Version 0.1.0 | Entry point: `cloudctl.cli:main`

## Global Options

| Flag | Description |
|---|---|
| `--version` | Print version (`cloudctl v0.1.0`) and exit |
| `--config, -c <path>` | Path to custom `cloud.yaml` configuration file |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | Logging verbosity (default: `INFO`) |
| `--json` | Output structured JSON logs |

---

## Commands

### `cloudctl setup`
One-command bootstrap: detects host, generates secrets, initializes storage, deploys containers.

| Flag | Description |
|---|---|
| `--dry-run` | Validate environment without modifying system |
| `--non-interactive` | Unattended mode (no prompts) |
| `--force, -f` | Overwrite existing configuration/secrets |
| `--name <name>` | Cloud instance identifier |
| `--domain <domain>` | Cloud instance domain |
| `--skip-smoke-test` | Skip post-installation smoke tests |

**Exit codes**: `0` success, `1` failure.

---

### `cloudctl init`
Initialize configuration and security credentials only.

| Flag | Description |
|---|---|
| `--force, -f` | Overwrite existing configuration |
| `--name <name>` | Cloud instance name |
| `--domain <domain>` | Domain or hostname |

---

### `cloudctl install`
Full automated container stack installation.

| Flag | Description |
|---|---|
| `--dry-run` | Validate and plan without applying |
| `--skip-smoke-test` | Skip post-installation smoke tests |

---

### `cloudctl start` / `stop` / `restart`
Start, stop, or restart all cloud containers and services. No additional arguments.

---

### `cloudctl status`
Display health status dashboard of all services.

| Flag | Description |
|---|---|
| `--json` | Output status in JSON format |

---

### `cloudctl doctor`
Run diagnostic health checks with remediation advice.

| Flag | Description |
|---|---|
| `--fix` | Attempt automatic remediation |

---

### `cloudctl update`
Safe system and container updates with pre-flight snapshot and rollback.

| Flag | Description |
|---|---|
| `--dry-run` | Simulate update without applying |

---

### `cloudctl backup`
Create encrypted Restic backup snapshot.

| Flag | Description |
|---|---|
| `--verify` | Verify cryptographic integrity after backup |
| `--tag <tag>` | Backup tag/label (default: `manual`) |

> **⚠️ Requires**: Restic CLI installed on host.

---

### `cloudctl restore`
Restore cloud state from encrypted backup snapshot.

| Flag | Description |
|---|---|
| `--snapshot <id>` | Snapshot ID to restore (default: `latest`) |
| `--dry-run` | Simulate restore without modifying files |
| `--test` | Test restore into isolated temporary directory |

> **⚠️ DESTRUCTIVE**: Overwrites current data with snapshot contents.

---

### `cloudctl migrate export` / `import`
Portable migration bundle management.

```bash
cloudctl migrate export --output uspc-backup.tar.gz
cloudctl migrate import --input uspc-backup.tar.gz
```

---

### `cloudctl uninstall`
Cleanly remove USPC services and runtime.

| Flag | Description |
|---|---|
| `--purge-data` | **⚠️ DESTRUCTIVE**: Purge all user data and backups |
| `--force, -f` | Bypass confirmation prompt |

---

### `cloudctl cleanup`
Clean cache, temporary files, and stale transcode assets.

| Flag | Description |
|---|---|
| `--dry-run` | Report reclaimable space without deleting |
| `--purge-thumbnails` | Purge cached thumbnail assets |
| `--purge-transcodes` | Purge cached transcoded videos |

---

### `cloudctl logs`
Stream or display aggregated service logs.

| Flag | Description |
|---|---|
| `--service, -s <name>` | Service name: `nextcloud`, `postgres`, `redis`, `media`, `headscale` |
| `--tail, -n <num>` | Number of recent log lines (default: 100) |
| `--follow, -f` | Follow live log output |

---

### `cloudctl config <action>`
Declarative configuration management.

| Subcommand | Description |
|---|---|
| `config validate` | Validate current config against JSON Schema |
| `config diff` | Show provenance for all settings (AUTO/DEFAULT/USER-OVERRIDE) |
| `config export [--output path] [--unmask-secrets]` | Export active configuration |
| `config import --input <path>` | Import and validate external configuration |
| `config migrate [--target-version <ver>]` | Migrate config schema (default target: 0.3.0) |

> **⚠️ CAUTION**: `--unmask-secrets` exposes raw secret values.

---

### `cloudctl orchestrator <action>`
Orchestration management.

| Subcommand | Description |
|---|---|
| `orchestrator status` | Display active orchestrator and workload status |
| `orchestrator switch <mode>` | Switch mode: `appliance`, `cluster`, `k3s` |
| `orchestrator nodes [--json]` | List active cluster/appliance nodes |
| `orchestrator scale <service> <replicas>` | Scale service replicas (cluster mode) |
| `orchestrator manifests [--output-dir path]` | Export declarative manifests |

---

### `cloudctl monitor`
Live terminal performance monitoring.

| Flag | Description |
|---|---|
| `--count, -n <num>` | Number of telemetry samples (default: 1) |
| `--interval, -i <sec>` | Sample interval seconds (default: 2.0) |
| `--profile` | `minimal`, `standard`, `full`, `cluster` |
| `--json` | Output telemetry in JSON format |
| `--prometheus` | Output in Prometheus exposition format |

---

### `cloudctl alerts`
Inspect active operational threshold alerts.

| Flag | Description |
|---|---|
| `--profile` | `minimal`, `standard`, `full`, `cluster` |
| `--acknowledge <id>` | Acknowledge alert by ID |
| `--resolve <id>` | Mark alert as resolved |
| `--simulate-cycle` | Simulate complete alert lifecycle |
| `--json` | Output alerts in JSON format |
| `--fail-on-critical` | Exit code 2 on critical alert |

---

### `cloudctl benchmark`
Measure disk IO, compute, and streaming capacity.

| Flag | Description |
|---|---|
| `--profile` | Force profile: `tiny`, `small`, `standard`, `performance`, `media` |
| `--load-profile` | Execute workload: `smoke`, `normal`, `heavy`, `media_heavy`, `multi_user`, `stress`, `soak` |
| `--stress` | Progressive concurrency stress test |
| `--soak` | Sustained endurance soak test |
| `--duration <sec>` | Soak test duration (default: 3.0) |
| `--json` | Output in JSON format |

---

### `cloudctl performance`
Display live system metrics, active users, and capacity.

| Flag | Description |
|---|---|
| `--json` | Output metrics in JSON format |

---

### `cloudctl readiness`
7-layer production readiness compliance check.

| Flag | Description |
|---|---|
| `--json` | Output readiness audit in JSON format |

---

### `cloudctl acceptance`
Automated production acceptance audit.

| Flag | Description |
|---|---|
| `--full` | Execute full acceptance lab in disposable sandbox |
| `--hardware` | Physical hardware WAN mesh evidence workflow |
| `--endpoint <ip:port>` | Target physical endpoint for hardware probe |
| `--strict` | Fail closed (exit 1) on any software gate failure |
| `--json` | Output in JSON format |
| `--output-dir, -o <path>` | Export all 12 report artifacts to directory |

---

### `cloudctl security-check`
Run comprehensive security audit.

| Flag | Description |
|---|---|
| `--strict` | Fail if any warning is detected |

---

### `cloudctl sbom`
Generate Software Bill of Materials.

| Flag | Description |
|---|---|
| `--format` | `text`, `json` (SPDX), `cyclonedx` |
| `--output, -o <path>` | Save SBOM to file |
| `--json` | Output JSON SPDX format |
| `--audit` | Audit 100% open-source compliance |
| `--verify-drift` | Verify SBOM completeness and package drift |

---

### `cloudctl test`
Execute automated test suite.

| Flag | Description |
|---|---|
| `--media-only` | Run media test suite only |
| `--coverage` | Generate coverage report |

---

### `cloudctl bundle create`
Create offline installation package.

| Flag | Description |
|---|---|
| `--output, -o <path>` | Output path (default: `uspc-offline-bundle.tar.gz`) |

---

## Cross-References

- [Configuration](CONFIGURATION.md) | [Architecture](ARCHITECTURE.md) | [Acceptance](ACCEPTANCE.md)
- [Setup Guides](setup/) | [Troubleshooting](TROUBLESHOOTING.md)
