"""Secure secret management for USPC."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from cloudctl.core.logging import get_logger, register_secret_for_masking
from cloudctl.utils.crypto import generate_base64_key, generate_hex_token, generate_secure_password
from cloudctl.utils.fs import atomic_write, ensure_directory

logger = get_logger("secrets")


@dataclass
class CloudSecrets:
    """Dataclass holding all required cloud credentials and keys."""

    postgres_password: str
    nextcloud_admin_password: str
    redis_password: str
    restic_password: str
    media_jwt_secret: str
    headscale_private_key: str
    headscale_noise_private_key: str


class SecretManager:
    """Manages creation, storage, and retrieval of sensitive deployment secrets."""

    def __init__(self, secrets_dir: str | Path | None = None):
        if secrets_dir:
            self.secrets_dir = Path(secrets_dir).expanduser().resolve()
        else:
            self.secrets_dir = Path("~/.uspc/secrets").expanduser().resolve()
        self.secrets_file = self.secrets_dir / "secrets.json"

    def load_or_generate_secrets(self, force: bool = False) -> CloudSecrets:
        """Load existing secrets from file, or generate new ones if not present or force is True."""
        if self.secrets_file.exists() and not force:
            try:
                with open(self.secrets_file, encoding="utf-8") as f:
                    data = json.load(f)
                secrets = CloudSecrets(
                    postgres_password=data["postgres_password"],
                    nextcloud_admin_password=data["nextcloud_admin_password"],
                    redis_password=data["redis_password"],
                    restic_password=data["restic_password"],
                    media_jwt_secret=data["media_jwt_secret"],
                    headscale_private_key=data["headscale_private_key"],
                    headscale_noise_private_key=data["headscale_noise_private_key"],
                )
                self._register_all_for_masking(secrets)
                return secrets
            except Exception as e:
                logger.warning(f"Failed to read existing secrets file, regenerating: {e}")

        # Generate fresh secure credentials
        secrets = CloudSecrets(
            postgres_password=generate_secure_password(32),
            nextcloud_admin_password=generate_secure_password(32),
            redis_password=generate_secure_password(32),
            restic_password=generate_secure_password(32),
            media_jwt_secret=generate_hex_token(32),
            headscale_private_key=generate_base64_key(32),
            headscale_noise_private_key=generate_base64_key(32),
        )
        self.save_secrets(secrets)
        self._register_all_for_masking(secrets)
        return secrets

    def save_secrets(self, secrets: CloudSecrets) -> None:
        """Atomically persist secrets with 0600 permissions."""
        ensure_directory(self.secrets_dir, mode=0o700)
        content = json.dumps(asdict(secrets), indent=2)
        atomic_write(self.secrets_file, content, mode=0o600)
        logger.info(f"Secrets securely stored at {self.secrets_file}")

    def _register_all_for_masking(self, secrets: CloudSecrets) -> None:
        """Register all secret values to prevent them from appearing in logs."""
        for val in asdict(secrets).values():
            if isinstance(val, str):
                register_secret_for_masking(val)
