# USPC SBOM & License Compliance

> Module: `src/cloudctl/commands/sbom_cmd.py`

## Overview

USPC maintains a complete Software Bill of Materials (SBOM) and enforces 100% free and open-source licensing with zero SaaS or proprietary dependencies.

---

## SBOM Formats

| Format | Standard | Command |
|---|---|---|
| SPDX 2.3 | ISO/IEC 5962:2021 | `cloudctl sbom --format json` |
| CycloneDX 1.5 | OWASP | `cloudctl sbom --format cyclonedx` |
| Text (human-readable) | — | `cloudctl sbom` |

---

## Commands

```bash
# Generate SPDX 2.3 JSON SBOM
cloudctl sbom --format json --output reports/SBOM.spdx.json

# Generate CycloneDX 1.5 JSON SBOM
cloudctl sbom --format cyclonedx --output reports/SBOM.cyclonedx.json

# Human-readable text output
cloudctl sbom

# Audit license compliance (100% FOSS check)
cloudctl sbom --audit

# Verify SBOM drift (package changes since last generation)
cloudctl sbom --verify-drift
```

---

## Dependency Inventory

### Python Runtime Dependencies

| Package | License | Purpose |
|---|---|---|
| `pyyaml` ≥ 6.0 | MIT | YAML parsing |
| `jsonschema` ≥ 4.20 | MIT | Config schema validation |
| `psutil` ≥ 5.9 | BSD-3 | System metrics |
| `cryptography` ≥ 41.0 | Apache-2.0/BSD | Cryptographic operations |
| `fastapi` ≥ 0.100 | MIT | Media service API |
| `uvicorn` ≥ 0.23 | BSD-3 | ASGI server |
| `pydantic` ≥ 2.0 | MIT | Data validation |
| `pillow` ≥ 10.0 | HPND | Image processing |
| `httpx` ≥ 0.25 | BSD-3 | HTTP client |
| `python-multipart` ≥ 0.0.6 | Apache-2.0 | File upload parsing |

### Container Images

| Image | License | Purpose |
|---|---|---|
| Nextcloud 27.1.4-apache | AGPL-3.0 | File sync/sharing |
| PostgreSQL 16.1-alpine | PostgreSQL License | Database |
| Redis 7.2-alpine | BSD-3 | Cache |
| Headscale | BSD-3 | VPN coordination |

### External Tools (Optional)

| Tool | License | Purpose |
|---|---|---|
| Restic | BSD-2 | Encrypted backups |
| FFmpeg | LGPL/GPL | Media transcoding |
| Prometheus | Apache-2.0 | Metrics (cluster mode) |
| Grafana | AGPL-3.0 | Dashboards (cluster mode) |
| Loki | AGPL-3.0 | Log aggregation (cluster mode) |
| Alertmanager | Apache-2.0 | Alerts (cluster mode) |

---

## License Policy

- **Allowed**: MIT, BSD, Apache-2.0, LGPL, AGPL, ISC, PSF, HPND, PostgreSQL.
- **Prohibited**: Any proprietary, SaaS-dependent, or phone-home license.
- **Enforcement**: `cloudctl sbom --audit` verifies 100% compliance.

---

## SBOM Drift Detection

`cloudctl sbom --verify-drift` compares current installed packages against the last generated SBOM to detect:
- Newly added dependencies
- Removed dependencies
- Version changes
- License changes

---

## CI/CD Integration

The security workflow (`.github/workflows/security.yml`) automatically:
1. Generates SPDX + CycloneDX SBOMs on every push.
2. Runs `cloudctl sbom --audit` to verify 100% FOSS compliance.
3. Uploads SBOM artifacts.

---

## Cross-References

- [Security](../SECURITY.md) | [CI/CD](CI-CD.md) | [Acceptance](ACCEPTANCE.md)
