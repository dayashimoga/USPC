# USPC Encrypted Backup, Verification & Disaster Recovery Guide

USPC integrates **Restic** for client-side encrypted, deduplicated, snapshot-based backups of PostgreSQL database dumps, Nextcloud file data, media libraries, and configuration state.

## Backup Commands

### Create an Encrypted Snapshot

```bash
./cloudctl backup
```

### Verify Cryptographic Integrity

Runs `restic check` to verify data packs and index integrity:

```bash
./cloudctl backup --verify
```

---

## Restore Operations

### Dry-Run Restore Simulation

Simulate what files would be restored without touching active storage:

```bash
./cloudctl restore --dry-run
```

### Isolated Test Restore

Restores snapshot into a temporary isolated sandbox to verify data extraction without impacting running services:

```bash
./cloudctl restore --test
```

### Full Production Restore

```bash
./cloudctl restore --snapshot latest
```

---

## Migration Between Machines

### 1. On Source Machine (Export)

```bash
./cloudctl migrate export --output uspc-migration-bundle.tar.gz
```

### 2. On New Machine (Import)

```bash
./cloudctl migrate import --input uspc-migration-bundle.tar.gz
```
