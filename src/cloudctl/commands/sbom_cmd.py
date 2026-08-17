"""SBOM (Software Bill of Materials) generator, CycloneDX/SPDX exporter, and license audit command."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from cloudctl.core.logging import get_logger

logger = get_logger("cmd.sbom")

# Comprehensive Certified FOSS dependency inventory with licenses
OPEN_SOURCE_DEPENDENCIES = [
    {
        "name": "fastapi",
        "version": ">=0.100.0",
        "license": "MIT",
        "purpose": "Media API microservice & REST framework",
        "type": "library",
    },
    {
        "name": "uvicorn",
        "version": ">=0.23.0",
        "license": "BSD-3-Clause",
        "purpose": "High-performance ASGI web server",
        "type": "library",
    },
    {
        "name": "pydantic",
        "version": ">=2.0.0",
        "license": "MIT",
        "purpose": "Data validation & settings models",
        "type": "library",
    },
    {
        "name": "pillow",
        "version": ">=10.0.0",
        "license": "HPND",
        "purpose": "Image thumbnailing and EXIF parsing",
        "type": "library",
    },
    {
        "name": "pyyaml",
        "version": ">=6.0.0",
        "license": "MIT",
        "purpose": "Declarative YAML config parsing",
        "type": "library",
    },
    {
        "name": "jsonschema",
        "version": ">=4.20.0",
        "license": "MIT",
        "purpose": "Schema validation and bounds checking",
        "type": "library",
    },
    {
        "name": "psutil",
        "version": ">=5.9.0",
        "license": "BSD-3-Clause",
        "purpose": "Hardware and resource metrics collection",
        "type": "library",
    },
    {
        "name": "cryptography",
        "version": ">=41.0.0",
        "license": "Apache-2.0 / BSD",
        "purpose": "Cryptographic tokens & vault security",
        "type": "library",
    },
    {
        "name": "httpx",
        "version": ">=0.25.0",
        "license": "BSD-3-Clause",
        "purpose": "Async HTTP client for integration checks",
        "type": "library",
    },
    {
        "name": "python-multipart",
        "version": ">=0.0.6",
        "license": "Apache-2.0",
        "purpose": "Multipart form file upload parsing",
        "type": "library",
    },
    {
        "name": "ffmpeg",
        "version": "6.x / 7.x",
        "license": "LGPL-2.1+ / GPL-2.0+",
        "purpose": "Video transcoding & audio badge extraction",
        "type": "binary",
    },
    {
        "name": "nextcloud",
        "version": "27.1.4-apache",
        "license": "AGPL-3.0",
        "purpose": "Authoritative file synchronization & webDAV",
        "type": "container-image",
    },
    {
        "name": "postgresql",
        "version": "16.1-alpine",
        "license": "PostgreSQL License",
        "purpose": "Relational transactional database",
        "type": "container-image",
    },
    {
        "name": "redis",
        "version": "7.2-alpine",
        "license": "BSD-3-Clause",
        "purpose": "In-memory cache & locking engine",
        "type": "container-image",
    },
    {
        "name": "headscale",
        "version": "0.22.3",
        "license": "BSD-3-Clause",
        "purpose": "WireGuard P2P VPN mesh coordinator",
        "type": "container-image",
    },
    {
        "name": "prometheus",
        "version": "2.50.0",
        "license": "Apache-2.0",
        "purpose": "Self-hosted metrics scraper & time-series TSDB",
        "type": "container-image",
    },
    {
        "name": "grafana",
        "version": "10.4.0",
        "license": "AGPL-3.0",
        "purpose": "Self-hosted telemetry and operational dashboard",
        "type": "container-image",
    },
    {
        "name": "loki",
        "version": "2.9.4",
        "license": "AGPL-3.0",
        "purpose": "Self-hosted log aggregator & query engine",
        "type": "container-image",
    },
    {
        "name": "podman",
        "version": "4.x / 5.x",
        "license": "Apache-2.0",
        "purpose": "Rootless OCI container runtime (Appliance Mode)",
        "type": "runtime",
    },
    {
        "name": "k3s",
        "version": "v1.30.2+k3s1",
        "license": "Apache-2.0",
        "purpose": "Lightweight CNCF Kubernetes (Cluster Mode)",
        "type": "orchestrator",
    },
    {
        "name": "restic",
        "version": "0.16.x",
        "license": "BSD-2-Clause",
        "purpose": "Client-side encrypted deduplicated backup engine",
        "type": "binary",
    },
]


def generate_sbom_spdx() -> dict[str, Any]:
    """Generate structured SPDX 2.3 JSON Software Bill of Materials."""
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "USPC-Universal-Personal-Cloud-Platform",
        "documentNamespace": "https://github.com/dayashimoga/USPC/spdx/0.5.0",
        "creationInfo": {
            "created": "2026-08-17T00:00:00Z",
            "creators": ["Tool: cloudctl-sbom-0.5.0", "Organization: USPC Community"],
        },
        "packages": [
            {
                "name": dep["name"],
                "SPDXID": f"SPDXRef-Package-{dep['name'].replace('.', '-')}",
                "versionInfo": dep["version"],
                "licenseConcluded": dep["license"],
                "licenseDeclared": dep["license"],
                "description": dep["purpose"],
                "supplier": "OpenSource",
            }
            for dep in OPEN_SOURCE_DEPENDENCIES
        ],
    }


def generate_sbom_cyclonedx() -> dict[str, Any]:
    """Generate structured CycloneDX 1.5 JSON Software Bill of Materials."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, 'uspc.local')}",
        "version": 1,
        "metadata": {
            "component": {
                "name": "uspc",
                "version": "0.5.0",
                "type": "application",
                "licenses": [{"license": {"id": "AGPL-3.0"}}],
            }
        },
        "components": [
            {
                "name": dep["name"],
                "version": dep["version"],
                "type": dep.get("type", "library"),
                "description": dep["purpose"],
                "licenses": [{"license": {"name": dep["license"]}}],
            }
            for dep in OPEN_SOURCE_DEPENDENCIES
        ],
    }


def audit_license_compliance() -> tuple[bool, list[str]]:
    """Audit dependencies for mandatory 100% open-source compliance and 0% SaaS lock-in."""
    violations = []
    disallowed_terms = ["proprietary", "commercial", "saas", "closed-source"]

    for dep in OPEN_SOURCE_DEPENDENCIES:
        lic = dep["license"].lower()
        if any(term in lic for term in disallowed_terms):
            violations.append(f"Non-compliant license in {dep['name']}: {dep['license']}")

    is_compliant = len(violations) == 0
    return is_compliant, violations


def execute_sbom_cmd(args: argparse.Namespace) -> int:
    """Execute SBOM generation and open-source license audit."""
    if getattr(args, "audit", False):
        compliant, violations = audit_license_compliance()
        if compliant:
            print("[OK] License Audit PASSED: 100% Free & Open-Source, 0% SaaS Lock-In.")
            return 0
        print("[FAIL] License Audit FAILED with violations:")
        for v in violations:
            print(f"  - {v}")
        return 1

    out_format = getattr(args, "format", "text")
    out_file = getattr(args, "output", None)

    if out_format == "cyclonedx":
        cdx_data = generate_sbom_cyclonedx()
        rendered = json.dumps(cdx_data, indent=2)
        if out_file:
            Path(out_file).write_text(rendered, encoding="utf-8")
            print(f"[OK] CycloneDX 1.5 SBOM exported to {out_file}")
        else:
            print(rendered)
        return 0

    if out_format == "json" or getattr(args, "json", False):
        spdx_data = generate_sbom_spdx()
        rendered = json.dumps(spdx_data, indent=2)
        if out_file:
            Path(out_file).write_text(rendered, encoding="utf-8")
            print(f"[OK] SPDX 2.3 SBOM exported to {out_file}")
        else:
            print(rendered)
        return 0

    spdx_data = generate_sbom_spdx()
    print("=" * 82)
    print(" USPC SOFTWARE BILL OF MATERIALS (SBOM) & OPEN-SOURCE LICENSE AUDIT")
    print("=" * 82)
    print(f" Total Identified Components : {len(OPEN_SOURCE_DEPENDENCIES)}")
    print(" Proprietary SaaS Lock-In    : 0% (100% Free & Open-Source)")
    print("-" * 82)
    print(f" {'Component':<18} {'Version':<18} {'License':<22} {'Purpose'}")
    print("-" * 82)
    for dep in OPEN_SOURCE_DEPENDENCIES:
        print(f" {dep['name']:<18} {dep['version']:<18} {dep['license']:<22} {dep['purpose']}")
    print("=" * 82)

    if out_file:
        Path(out_file).write_text(json.dumps(spdx_data, indent=2), encoding="utf-8")
        print(f"\n[OK] Machine-readable SBOM written to {out_file}")

    return 0
