# USPC Upgrade & Migration

> Module: `src/cloudctl/core/migration.py`, `src/cloudctl/commands/update.py`

## Upgrade Procedure

### Safe Update with Rollback

```bash
# Preview update without changes
cloudctl update --dry-run

# Apply update (automatic pre-flight backup snapshot)
cloudctl update
```

`cloudctl update` performs:
1. Pre-flight backup snapshot.
2. Container image version check.
3. Rolling update of container images.
4. Post-update health check.
5. Automatic rollback on failure.

---

## Configuration Migration

```bash
# Migrate config schema to newer version
cloudctl config migrate --target-version 0.3.0
```

Configuration migration:
1. Reads current `cloud.yaml`.
2. Merges with latest `defaults.yaml` to add new fields.
3. Translates deprecated keys.
4. Bumps version tag.
5. Validates against schema.
6. Writes atomically.

---

## Host Migration

### Export
```bash
# On source machine
cloudctl migrate export --output uspc-migration.tar.gz
```

Exports:
- User data (`~/.uspc/data/`)
- Configuration (`~/.uspc/config/`)
- Secrets vault (`~/.uspc/secrets/`)
- PostgreSQL database dump

### Import
```bash
# On destination machine
cloudctl migrate import --input uspc-migration.tar.gz
```

Imports:
- Validates tar member paths (tar-slip protection).
- Extracts to correct directories.
- Restores PostgreSQL database.
- Validates configuration.

---

## Orchestrator Mode Switching

```bash
# Current mode
cloudctl orchestrator status

# Switch to K3s Cluster
cloudctl orchestrator switch cluster

# Switch back to Podman Appliance
cloudctl orchestrator switch appliance
```

**Important**:
- Stop services before switching: `cloudctl stop`.
- Data and configuration are preserved.
- K3s manifests are automatically applied when switching to cluster mode.

---

## Version History

See [CHANGELOG.md](../CHANGELOG.md) for all version changes.

| Version | Key Changes |
|---|---|
| 0.5.0 | 100% production acceptance, CycloneDX, security modernization |
| 0.4.0 | Switchable orchestrator, observability stack, acceptance lab |
| 0.3.0 | Readiness audit, config management, token revocation |
| 0.2.0 | Auth hardening, fairness, cleanup, vulnerability fixes |
| 0.1.0 | Initial release — core CLI, media, backup, networking |

---

## Rollback

If an update fails:
```bash
# Restore from pre-update snapshot
cloudctl restore --snapshot latest

# Restart services
cloudctl restart
```

---

## Cross-References

- [Backup & DR](BACKUP-DR.md) | [Configuration](CONFIGURATION.md) | [Changelog](../CHANGELOG.md)
