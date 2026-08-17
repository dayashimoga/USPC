"""Comprehensive tests for configuration diff, export, import, provenance, and CLI commands."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from cloudctl.commands.config_cmd import execute_config
from cloudctl.core.config import ConfigManager


def test_config_diff_and_provenance(temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_data = {
        "version": "0.1.0",
        "cloud": {
            "name": "custom_name",
            "domain": "custom.domain.local",
            "admin_user": "custom_admin",
        },
        "performance": {
            "profile": "auto",
        },
    }
    cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    cm = ConfigManager(config_path=cfg_file)
    diffs = cm.diff_config()
    assert len(diffs) > 0

    # Verify provenance markings
    keys = {d["key"]: d for d in diffs}
    assert "cloud.name" in keys
    assert keys["cloud.name"]["provenance"] == "USER-OVERRIDE"
    assert keys["cloud.name"]["current"] == "custom_name"


def test_config_export_masked_and_unmasked(temp_dir: Path):
    cm = ConfigManager()

    # Masked export
    masked_yaml = cm.export_config(mask_secrets=True)
    assert isinstance(masked_yaml, str)

    # Unmasked export
    unmasked_yaml = cm.export_config(mask_secrets=False)
    assert isinstance(unmasked_yaml, str)


def test_config_import_and_backup(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    imported_dict = deepcopy(mock_config_dict)
    imported_dict["cloud"]["name"] = "imported_cloud"
    new_cfg_file = temp_dir / "new_cloud.yaml"
    new_cfg_file.write_text(yaml.dump(imported_dict), encoding="utf-8")

    cm = ConfigManager(config_path=cfg_file)
    assert cm.import_config(new_cfg_file, backup_existing=True)
    assert cfg_file.with_suffix(".yaml.bak").exists()
    assert "imported_cloud" in cfg_file.read_text(encoding="utf-8")

    # Non-existent file error
    with pytest.raises(FileNotFoundError):
        cm.import_config(temp_dir / "does_not_exist.yaml")


def test_execute_config_cli_dispatch(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # Validate action
    args_val = MagicMock(config=str(cfg_file), config_action="validate")
    assert execute_config(args_val) == 0

    # Diff action
    args_diff = MagicMock(config=str(cfg_file), config_action="diff")
    assert execute_config(args_diff) == 0

    # Export to file
    out_file = temp_dir / "exported.yaml"
    args_exp = MagicMock(
        config=str(cfg_file), config_action="export", output=str(out_file), unmask_secrets=False
    )
    assert execute_config(args_exp) == 0
    assert out_file.exists()

    # Export to stdout
    args_exp_stdout = MagicMock(
        config=str(cfg_file), config_action="export", output=None, unmask_secrets=True
    )
    assert execute_config(args_exp_stdout) == 0

    # Import action
    imp_src = temp_dir / "imp.yaml"
    imp_data = deepcopy(mock_config_dict)
    imp_data["cloud"]["name"] = "imported_via_cli"
    imp_src.write_text(yaml.dump(imp_data), encoding="utf-8")
    args_imp = MagicMock(config=str(cfg_file), config_action="import", input=str(imp_src))
    assert execute_config(args_imp) == 0

    # Import missing --input
    args_imp_err = MagicMock(config=str(cfg_file), config_action="import", input=None)
    assert execute_config(args_imp_err) == 1

    # Invalid action
    args_inv = MagicMock(config=str(cfg_file), config_action="unknown_action")
    assert execute_config(args_inv) == 1
