# USPC Security Architecture & Hardening Guide

USPC is engineered with a private-access default model to ensure zero unauthorized public network exposure.

## Security Controls

1. **Private Mesh Overlay**: WireGuard kernel module or userspace tunnel with Headscale coordination. No ports open to public IPv4/IPv6 internet.
2. **Strict Secret Management**: Cryptographic secrets, passwords, and JWT tokens are stored in `~/.uspc/secrets/` with strict `0600` permissions (directory `0700`). Secrets are automatically masked from all logs and CLI stdout.
3. **Encrypted Backups**: Restic AES-256 (GCM) encrypted backup snapshots with integrity verification.
4. **Least Privilege Container Runtime**: Podman/Docker execution in rootless mode where supported.
5. **Path Traversal Protection**: All file read/write access is validated via canonical path resolution preventing directory escapes.
6. **Token-Based Media Authentication**: Time-limited HMAC tokens for streaming and thumbnail access.

---

## Running Automated Security Audits

```bash
./cloudctl security-check
```

Enforce strict mode in CI/CD pipelines (fails if any warning is detected):

```bash
./cloudctl security-check --strict
```
