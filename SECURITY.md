# Security Policy

The Universal Personal Cloud Platform (USPC) takes security seriously. As a self-hosted personal cloud platform designed to protect private data and media, we are committed to maintaining the highest security standards.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in USPC, please follow these steps:

1. **Do not disclose publicly**: Do not create public GitHub issues or forum posts regarding suspected security vulnerabilities.
2. **Contact maintainers**: Email security reports to `security@uspc-project.local` (or file a private security advisory on GitHub).
3. **Include details**:
   - Component affected (e.g., `cloudctl`, `uspc-media`, `headscale`, `restic`)
   - Type of vulnerability (e.g., authentication bypass, arbitrary command execution, SSRF, path traversal)
   - Step-by-step reproduction instructions or proof-of-concept
   - Impact assessment
4. **Response timeline**:
   - Initial acknowledgement: Within 48 hours
   - Triage and severity assessment: Within 5 business days
   - Fix and advisory release: Coordinated disclosure based on severity

## Core Security Architecture

1. **Private Access Default**: USPC operates on a private VPN model (WireGuard + Headscale). No public internet ports are exposed by default.
2. **Secret Management**: All generated secrets (passwords, JWT keys, WireGuard keys, Restic encryption keys) are stored in secure locations (`~/.uspc/secrets/` with mode `0600`) and are never logged, committed to version control, or exposed in error messages.
3. **Least Privilege**: Container workloads run without `--privileged` flags and with read-only root filesystems where applicable.
4. **Encrypted Backups**: Backups created via Restic are encrypted with AES-256 in Galois/Counter Mode (GCM).
5. **Authenticated Media Streaming**: Media streaming and thumbnail endpoints require valid session tokens or cryptographic bearer tokens. Path traversal is strictly prevented via strict path canonicalization.
6. **No SaaS / Vendor Lock-in**: All security controls are 100% open source and self-hosted with no telemetry or external phone-home dependencies.
