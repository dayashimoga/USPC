#!/usr/bin/env bash
# USPC Software Bill of Materials (SBOM) Generator
set -euo pipefail

echo "==> Generating USPC Software Bill of Materials (SBOM)..."

cat <<EOF > USPC_SBOM.json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "metadata": {
    "component": {
      "name": "USPC",
      "version": "0.1.0",
      "type": "application",
      "licenses": [{"license": {"id": "AGPL-3.0"}}]
    }
  },
  "components": [
    { "name": "Nextcloud Community", "version": "27.1.4", "license": "AGPL-3.0" },
    { "name": "PostgreSQL", "version": "16.1", "license": "PostgreSQL" },
    { "name": "Redis", "version": "7.2", "license": "BSD-3-Clause" },
    { "name": "Headscale", "version": "0.22.3", "license": "BSD-3-Clause" },
    { "name": "Restic", "version": "0.16.2", "license": "BSD-2-Clause" },
    { "name": "FFmpeg", "version": "6.1.1", "license": "LGPL-2.1" },
    { "name": "FastAPI", "version": "0.100+", "license": "MIT" },
    { "name": "Pillow", "version": "10.0+", "license": "HPND" }
  ]
}
EOF

echo "[+] SBOM generated at USPC_SBOM.json"
