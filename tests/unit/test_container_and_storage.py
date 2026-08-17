"""Unit tests for container abstraction and storage manager."""

from pathlib import Path

from cloudctl.core.container import ContainerManager, ContainerStatus
from cloudctl.core.storage import StorageManager


def test_container_manager_abstraction():
    cm = ContainerManager()
    assert cm.engine in ("podman", "docker")
    version = cm.get_version()
    assert version is not None

    status = cm.get_container_status("non-existent-container-xyz")
    assert isinstance(status, ContainerStatus)
    assert status.status in ("stopped", "unknown")


def test_storage_manager(temp_dir: Path):
    data_p = temp_dir / "data"
    cfg_p = temp_dir / "config"
    sm = StorageManager(data_path=data_p, config_path=cfg_p, min_free_space_gb=0.1)

    paths = sm.initialize_storage()
    assert paths.nextcloud_data.exists()
    assert paths.postgres_data.exists()
    assert paths.redis_data.exists()
    assert paths.media_cache.exists()
    assert paths.nextcloud_config.exists()
    assert paths.headscale_config.exists()

    # Read/write verification test
    assert sm.verify_read_write(paths.nextcloud_data) is True

    # Data migration test
    target_p = temp_dir / "migrated_data"
    test_file = paths.nextcloud_data / "important_file.txt"
    test_file.write_text("critical_user_payload", encoding="utf-8")

    sm.migrate_data(target_p)
    migrated_file = target_p / "nextcloud" / "important_file.txt"
    assert migrated_file.exists()
    assert migrated_file.read_text(encoding="utf-8") == "critical_user_payload"
