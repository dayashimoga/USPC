# USPC Dependencies

> Source: `pyproject.toml` | License: All FOSS

## Runtime Dependencies

| Package | Min Version | License | Purpose |
|---|---|---|---|
| `pyyaml` | ≥ 6.0.0 | MIT | YAML configuration parsing |
| `jsonschema` | ≥ 4.20.0 | MIT | JSON Schema config validation |
| `psutil` | ≥ 5.9.0 | BSD-3-Clause | System metrics (CPU, RAM, disk, IO) |
| `cryptography` | ≥ 41.0.0 | Apache-2.0 / BSD-3 | Cryptographic operations |
| `fastapi` | ≥ 0.100.0 | MIT | Media service HTTP API |
| `uvicorn` | ≥ 0.23.0 | BSD-3-Clause | ASGI server for FastAPI |
| `pydantic` | ≥ 2.0.0 | MIT | Data model validation |
| `pillow` | ≥ 10.0.0 | HPND | Image processing, thumbnails |
| `httpx` | ≥ 0.25.0 | BSD-3-Clause | HTTP client |
| `python-multipart` | ≥ 0.0.6 | Apache-2.0 | Multipart file upload parsing |

## Development Dependencies

| Package | Min Version | License | Purpose |
|---|---|---|---|
| `pytest` | ≥ 7.4.0 | MIT | Test framework |
| `pytest-cov` | ≥ 4.1.0 | MIT | Coverage measurement |
| `pytest-asyncio` | ≥ 0.21.0 | Apache-2.0 | Async test support |
| `pytest-mock` | ≥ 3.11.0 | MIT | Mocking utilities |
| `ruff` | ≥ 0.1.0 | MIT | Linter & formatter |

## External Tools (Optional, Not Bundled)

| Tool | License | Required For |
|---|---|---|
| Podman | Apache-2.0 | Container runtime (default) |
| Docker | Apache-2.0 | Alternative container runtime |
| K3s | Apache-2.0 | Cluster mode |
| Restic | BSD-2-Clause | Encrypted backups |
| FFmpeg | LGPL/GPL | Media transcoding & video thumbnails |
| Headscale | BSD-3-Clause | VPN coordination |
| Prometheus | Apache-2.0 | Metrics (cluster mode) |
| Grafana | AGPL-3.0 | Dashboards (cluster mode) |
| Loki | AGPL-3.0 | Log aggregation (cluster mode) |
| Alertmanager | Apache-2.0 | Alerts (cluster mode) |

## Container Images (Version-Pinned)

| Image | Tag | License |
|---|---|---|
| `nextcloud` | `27.1.4-apache` | AGPL-3.0 |
| `postgres` | `16.1-alpine` | PostgreSQL License |
| `redis` | `7.2-alpine` | BSD-3-Clause |

## Python Version

- **Required**: ≥ 3.10
- **CI tested**: 3.10, 3.11, 3.12

## Build System

- `setuptools` ≥ 83.0.0
- `wheel`

---

## Cross-References

- [SBOM & License](SBOM-LICENSE.md) | [Configuration](CONFIGURATION.md) | [Architecture](ARCHITECTURE.md)
