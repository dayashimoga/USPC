# USPC Testing

> 222 tests | 95.66% coverage | 0 skipped | 0 Ruff errors | 0 Bandit issues

## Test Commands

```bash
# Full test suite with coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=95

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/media/                   # Media service tests
pytest tests/integration/             # Integration tests
pytest tests/e2e/                     # Browser E2E tests
pytest tests/cross_platform/          # Cross-platform tests

# Quality checks
ruff check src/ tests/                # Linter
ruff format --check src/ tests/       # Format check
bandit -r src/ -ll -ii                # Security static analysis
```

---

## Test Directory Structure

```
tests/
├── conftest.py                          # Shared fixtures (temp_dir, mock_config_dict, etc.)
├── unit/                                # 41 test files, ~180 tests
│   ├── test_acceptance_report.py        # AcceptanceReport generation
│   ├── test_all_commands.py             # CLI command dispatch
│   ├── test_auth_revocation.py          # Token revocation
│   ├── test_backup_and_migration.py     # Backup/restore/migration
│   ├── test_bench_and_stress.py         # Benchmark & stress
│   ├── test_cli_commands.py             # CLI parsing
│   ├── test_config.py                   # Config load/validate/merge
│   ├── test_config_hardened.py          # Config edge cases
│   ├── test_container_and_storage.py    # Container & storage
│   ├── test_core_coverage.py            # Core module coverage
│   ├── test_deep_module_coverage.py     # Deep branch coverage
│   ├── test_destructive_dr.py           # DR lifecycle (create→hash→wipe→restore→verify)
│   ├── test_detect_and_secrets.py       # Host detection & secrets
│   ├── test_failure_injection.py        # Fault injection
│   ├── test_k3s_manifests.py            # K3s YAML validation
│   ├── test_monitoring_and_alerts.py    # Metrics & alerts
│   ├── test_orchestrator.py             # Orchestrator ABC & backends
│   ├── test_production_acceptance_gap_closure.py  # 12-report export
│   ├── test_resilience.py               # Resilience & recovery
│   ├── test_security_attacks.py         # Security attack vectors
│   ├── test_security_hardened.py        # Security edge cases
│   ├── test_soak_and_load_profiles.py   # Soak & load profiles
│   ├── test_storage_dr.py              # Storage DR
│   ├── test_upgrade_rollback.py         # Upgrade/rollback
│   ├── test_validators.py              # Input validation
│   ├── test_zenith_coverage.py          # Final coverage sweep
│   └── ...
├── media/                               # 6 test files, ~20 tests
│   ├── test_api_integration.py          # FastAPI endpoint integration
│   ├── test_auth_and_transcoder.py      # Auth + transcoder
│   ├── test_media_hardened.py           # Media edge cases
│   ├── test_models.py                   # SQLite media database
│   ├── test_scanner_and_indexer.py      # Filesystem scanning
│   └── test_streaming.py               # Range streaming
├── integration/                         # 2 test files
│   ├── test_multiuser_acceptance.py     # Multi-user scenarios
│   └── test_multiuser_load.py           # Concurrent load
├── e2e/                                 # 1 test file, 4 tests
│   ├── Dockerfile                       # Playwright container
│   └── test_browser_media.py            # Dual-mode: Playwright / DOM validation
└── cross_platform/                      # 2 test files
    ├── test_cross_platform.py           # OS detection
    └── test_network_mesh.py             # Network mesh config
```

---

## Evidence Taxonomy

| Level | Description | Example |
|---|---|---|
| `UNIT` | Isolated function/class tests | `test_config.py` |
| `INTEGRATION` | Multi-component interaction | `test_multiuser_load.py` |
| `CONTAINER` | Tests requiring Docker/Podman | E2E Playwright container |
| `BROWSER` | Browser automation or DOM validation | `test_browser_media.py` |
| `VM` | Virtual machine environment tests | CI matrix (ubuntu/windows/macos) |
| `HARDWARE` | Physical multi-device tests | `cloudctl acceptance --hardware` |

---

## Skipped Test Policy

**Zero skipped tests.** Every test must either:
1. Execute fully, OR
2. Provide a dual-mode fallback (e.g., Playwright → DOM validation).

Tests must never be marked `@pytest.mark.skip` without a corresponding fallback execution path.

---

## Coverage Requirements

- **Minimum**: 95.0% (`fail_under = 95` in `pyproject.toml`)
- **Critical modules** (auth, secrets): 100%
- **Core modules**: ≥94%

---

## Cross-References

- [Acceptance](ACCEPTANCE.md) | [CI/CD](CI-CD.md) | [Project Status](../PROJECT_STATUS.md)
