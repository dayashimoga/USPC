"""Unit tests for configuration loading, schema validation, and merging."""

from pathlib import Path

import pytest

from cloudctl.core.config import ConfigManager, deep_merge


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}, "e": 5}
    merged = deep_merge(base, override)
    assert merged == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}


def test_config_loader_and_schema_validation(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    mgr = ConfigManager(config_path=cfg_file)

    # Validate valid config
    mgr.validate(mock_config_dict)

    # Save and reload
    mgr.save_config(mock_config_dict)
    assert cfg_file.exists()

    loaded = mgr.load_config()
    assert loaded["cloud"]["name"] == "testcloud"
    assert loaded["services"]["postgres"]["port"] == 5432


def test_config_validation_rejections(mock_config_dict: dict):
    mgr = ConfigManager()

    # 1. Invalid CIDR
    bad_cidr = dict(mock_config_dict)
    bad_cidr["network"] = dict(mock_config_dict["network"])
    bad_cidr["network"]["vpn_subnet"] = "not-a-cidr"
    with pytest.raises(ValueError, match="Configuration error at \\[network -> vpn_subnet\\]"):
        mgr.validate(bad_cidr)

    # 2. Port collision
    collision = dict(mock_config_dict)
    collision["services"] = dict(mock_config_dict["services"])
    collision["services"]["postgres"] = dict(mock_config_dict["services"]["postgres"])
    collision["services"]["postgres"]["port"] = 8081  # Same as Nextcloud 8081
    with pytest.raises(ValueError, match="Port collision"):
        mgr.validate(collision)

    # 3. Invalid port number
    bad_port = dict(mock_config_dict)
    bad_port["services"]["postgres"]["port"] = 999999
    with pytest.raises(ValueError):
        mgr.validate(bad_port)

    # 4. Unknown root property rejected by schema
    extra_key = dict(mock_config_dict)
    extra_key["unsupported_custom_key"] = "test"
    with pytest.raises(ValueError, match="Configuration error"):
        mgr.validate(extra_key)
