# USPC Security Threat Model

## Assets Protected
1. **User Personal Files & Photos/Videos**: Confidentiality and integrity.
2. **PostgreSQL Database & App Metadata**: Availability and consistency.
3. **Cryptographic Private Keys & Secrets**: Integrity and confidentiality.

## Threat Vectors & Mitigations

| Threat | Risk | Mitigation |
|---|---|---|
| **Public Port Scanning & Ingress Attacks** | High | Default private mode via WireGuard/Headscale; zero public ingress ports. |
| **Directory Traversal (`../..`)** | High | Strict canonicalization via `validate_file_access` & `is_safe_path`. |
| **Cross-User Media Streaming Interception** | Medium | Time-limited cryptographic HMAC bearer tokens per media item. |
| **Storage Exhaustion / Denial of Service** | Medium | Per-user rate limiting, streaming concurrency caps, and free space enforcement. |
| **Data Loss / Host Disk Failure** | High | AES-256 client-side encrypted Restic backups with automated verification. |
| **Credential Leakage in Git / Logs** | High | Automatic regex secret masking in logs and Git exclusion of `secrets/` and `config/cloud.yaml`. |
