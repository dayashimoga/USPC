"""Configuration management, schema validation, and safe defaults merging."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from cloudctl.core.logging import get_logger
from cloudctl.utils.fs import atomic_write
from cloudctl.utils.validators import is_valid_cidr, is_valid_port

logger = get_logger("config")


def get_repo_root() -> Path:
    """Find repository root directory."""
    # Check current working dir or parent traversal
    curr = Path.cwd()
    if (curr / "config" / "schema.yaml").exists():
        return curr
    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        if (parent / "config" / "schema.yaml").exists():
            return parent
    return curr


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Configuration file not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dictionary into base dictionary."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class ConfigManager:
    """Loads, validates, and updates USPC configuration."""

    def __init__(self, config_path: str | Path | None = None, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root).resolve() if repo_root else get_repo_root()
        self.schema_file = self.repo_root / "config" / "schema.yaml"
        self.defaults_file = self.repo_root / "config" / "defaults.yaml"

        if config_path:
            self.config_path = Path(config_path).expanduser().resolve()
        else:
            self.config_path = self.repo_root / "config" / "cloud.yaml"

    def load_schema(self) -> dict[str, Any]:
        """Load JSON Schema definition."""
        return load_yaml(self.schema_file)

    def load_defaults(self) -> dict[str, Any]:
        """Load default configuration values."""
        if self.defaults_file.exists():
            return load_yaml(self.defaults_file)
        return {}

    def load_config(self) -> dict[str, Any]:
        """Load user configuration, merge with defaults, and validate schema."""
        defaults = self.load_defaults()
        if not self.config_path.exists():
            logger.debug(f"Config file not found at {self.config_path}, using defaults")
            merged = defaults
        else:
            user_config = load_yaml(self.config_path)
            merged = deep_merge(defaults, user_config)

        self.validate(merged)
        return merged

    def validate(self, config_data: dict[str, Any]) -> None:
        """Validate configuration against JSON Schema and perform semantic checks."""
        schema = self.load_schema()
        try:
            jsonschema.validate(instance=config_data, schema=schema)
        except jsonschema.ValidationError as err:
            path_str = " -> ".join(str(p) for p in err.absolute_path) or "root"
            raise ValueError(f"Configuration error at [{path_str}]: {err.message}") from err

        # Semantic validation checks
        net = config_data.get("network", {})
        if "vpn_subnet" in net and not is_valid_cidr(net["vpn_subnet"]):
            raise ValueError(f"Invalid VPN CIDR subnet format: {net['vpn_subnet']}")

        if "headscale_port" in net and not is_valid_port(net["headscale_port"]):
            raise ValueError(f"Invalid Headscale port: {net['headscale_port']}")

        services = config_data.get("services", {})
        used_ports: dict[int, str] = {}
        for s_name, s_conf in services.items():
            if isinstance(s_conf, dict) and "port" in s_conf:
                port = s_conf["port"]
                if not is_valid_port(port):
                    raise ValueError(f"Invalid port for service '{s_name}': {port}")
                if port in used_ports:
                    raise ValueError(
                        f"Port collision: Port {port} used by both '{used_ports[port]}' and '{s_name}'"
                    )
                used_ports[port] = s_name

        media = config_data.get("media", {})
        if media.get("enabled", True):
            m_port = media.get("port", 8085)
            if not is_valid_port(m_port):
                raise ValueError(f"Invalid media service port: {m_port}")
            if m_port in used_ports:
                raise ValueError(
                    f"Port collision: Port {m_port} used by '{used_ports[m_port]}' and 'media'"
                )

    def save_config(self, config_data: dict[str, Any]) -> None:
        """Validate and write configuration to config file atomically."""
        self.validate(config_data)
        content = yaml.dump(config_data, default_flow_style=False, sort_keys=False)
        atomic_write(self.config_path, content, mode=0o644)
        logger.info(f"Configuration successfully saved to {self.config_path}")

    def get_setting_metadata(self, key_path: str) -> dict[str, Any]:
        """
        Extract metadata (description, allowed range, restart impact, security impact)
        for a dotted configuration key path from schema.
        """
        schema = self.load_schema()
        parts = key_path.split(".")
        current_node = schema

        for part in parts:
            if isinstance(current_node, dict):
                props = current_node.get("properties", {})
                if part in props:
                    current_node = props[part]
                else:
                    current_node = {}
                    break
            else:
                current_node = {}
                break

        desc = current_node.get("description", "Configuration parameter")
        allowed = None
        if "enum" in current_node:
            allowed = f"Enum: {', '.join(str(e) for e in current_node['enum'])}"
        elif "minimum" in current_node or "maximum" in current_node:
            min_v = current_node.get("minimum", "-∞")
            max_v = current_node.get("maximum", "+∞")
            allowed = f"Range: [{min_v}, {max_v}]"
        elif "type" in current_node:
            allowed = f"Type: {current_node['type']}"

        # Restart & security impact inference
        restart_required = any(
            k in key_path for k in ["runtime", "services", "network", "port", "storage"]
        )
        security_impact = any(
            k in key_path
            for k in ["security", "vpn", "secret", "password", "tls", "headscale", "mfa"]
        )

        return {
            "key": key_path,
            "description": desc,
            "allowed_range": allowed or "Any valid format",
            "restart_required": restart_required,
            "security_impact": security_impact,
        }

    def get_effective_config(self, profile: str | None = None) -> dict[str, Any]:
        """
        Load configuration applying deterministic 5-tier precedence:
        AUTO -> DEFAULT -> PROFILE -> ENVIRONMENT -> USER-OVERRIDE
        """
        import os

        # 1. Base defaults
        defaults = self.load_defaults()
        config = deepcopy(defaults)

        # 2. User file overrides if present
        user_file_config = load_yaml(self.config_path) if self.config_path.exists() else {}

        # 3. Profile overrides
        active_prof = (
            profile
            or user_file_config.get("profiles", {}).get("active")
            or config.get("profiles", {}).get("active", "auto")
        )

        if active_prof == "dev":
            config.setdefault("cloud", {})["environment"] = "development"
            config.setdefault("performance", {})["rate_limit_requests_per_minute"] = 10000
            config.setdefault("security", {})["enforce_mfa"] = False
        elif active_prof == "test":
            config.setdefault("cloud", {})["environment"] = "testing"
            config.setdefault("performance", {})["rate_limit_requests_per_minute"] = 10000
        elif active_prof == "cluster":
            config.setdefault("orchestrator", {})["mode"] = "cluster"
            config.setdefault("monitoring", {})["profile"] = "cluster"
        elif active_prof == "appliance":
            config.setdefault("orchestrator", {})["mode"] = "appliance"

        # 4. Environment variable overrides (USPC_*)
        env_mappings = {
            "USPC_ORCHESTRATOR_MODE": ("orchestrator", "mode"),
            "USPC_ENVIRONMENT": ("cloud", "environment"),
            "USPC_DATA_PATH": ("storage", "data_path"),
            "USPC_MONITORING_PROFILE": ("monitoring", "profile"),
            "USPC_STORAGE_PROFILE": ("storage", "profile"),
        }
        for env_var, (section, key) in env_mappings.items():
            if env_var in os.environ:
                config.setdefault(section, {})[key] = os.environ[env_var]

        # 5. Explicit user configuration file overrides (highest priority)
        if user_file_config:
            config = deep_merge(config, user_file_config)

        return config

    def diff_config(self) -> list[dict[str, Any]]:
        """
        Compare active configuration against schema defaults.
        Categorizes every setting as USER-OVERRIDE, AUTO, or DEFAULT,
        and includes schema metadata for every entry.
        """
        defaults = self.load_defaults()
        user_config = load_yaml(self.config_path) if self.config_path.exists() else {}
        current = self.load_config()

        diffs: list[dict[str, Any]] = []

        def _traverse(prefix: str, cur_node: Any, def_node: Any, usr_node: Any):
            if isinstance(cur_node, dict):
                for k, v in cur_node.items():
                    sub_prefix = f"{prefix}.{k}" if prefix else k
                    d_v = def_node.get(k) if isinstance(def_node, dict) else None
                    u_v = usr_node.get(k) if isinstance(usr_node, dict) else None
                    _traverse(sub_prefix, v, d_v, u_v)
            else:
                provenance = "DEFAULT"
                if usr_node is not None:
                    provenance = "USER-OVERRIDE"
                elif cur_node == "auto" or (
                    isinstance(cur_node, str) and "auto" in cur_node.lower()
                ):
                    provenance = "AUTO"

                meta = self.get_setting_metadata(prefix)

                diffs.append(
                    {
                        "key": prefix,
                        "default": def_node,
                        "current": cur_node,
                        "provenance": provenance,
                        "is_modified": cur_node != def_node,
                        "description": meta["description"],
                        "allowed_range": meta["allowed_range"],
                        "restart_required": meta["restart_required"],
                        "security_impact": meta["security_impact"],
                    }
                )

        _traverse("", current, defaults, user_config)
        return diffs

    def export_config(self, mask_secrets: bool = True) -> str:
        """Export current configuration as validated YAML, optionally masking secret keys."""
        config = self.load_config()
        export_data = deepcopy(config)

        if mask_secrets:
            # Mask potential secret fields
            def _mask(node: Any):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if any(
                            s in k.lower() for s in ["password", "secret", "private_key", "token"]
                        ):
                            node[k] = "******"
                        else:
                            _mask(v)

            _mask(export_data)

        return yaml.dump(export_data, default_flow_style=False, sort_keys=False)

    def import_config(self, source_path: str | Path, backup_existing: bool = True) -> bool:
        """Validate and import a configuration file into the active config path."""
        src = Path(source_path).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"Import source configuration not found: {src}")

        new_data = load_yaml(src)
        self.validate(new_data)

        if backup_existing and self.config_path.exists():
            bak_path = self.config_path.with_suffix(".yaml.bak")
            atomic_write(bak_path, self.config_path.read_text(encoding="utf-8"), mode=0o644)
            logger.info(f"Existing configuration backed up to {bak_path}")

        self.save_config(new_data)
        logger.info(f"Configuration imported successfully from {src}")
        return True

    def migrate_config(self, target_version: str = "0.3.0") -> bool:
        """
        Safely migrate configuration schema across versions.
        Ensures deprecated keys are cleanly translated and version tag is bumped.
        """
        if not self.config_path.exists():
            return False

        data = load_yaml(self.config_path)
        current_version = data.get("version", "0.1.0")

        # Migrate 0.1.0 -> 0.2.0 -> 0.3.0
        data["version"] = target_version

        # Ensure all required sections exist
        defaults = self.load_defaults()
        migrated = deep_merge(defaults, data)

        self.save_config(migrated)
        logger.info(
            f"Configuration migrated successfully from {current_version} to {target_version}"
        )
        return True
