"""Structured and console logging for USPC."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


class SecretMaskingFormatter(logging.Formatter):
    """Logging formatter that masks known secrets and formats output nicely."""

    def __init__(self, json_format: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_format = json_format
        self.secrets: set[str] = set()

    def add_secret(self, secret: str) -> None:
        if secret and len(secret) > 3:
            self.secrets.add(secret)

    def mask(self, text: str) -> str:
        if not text or not self.secrets:
            return text
        res = text
        for s in self.secrets:
            if s in res:
                res = res.replace(s, "********")
        return res

    def format(self, record: logging.LogRecord) -> str:
        record_msg = self.mask(super().format(record))
        if self.json_format:
            payload = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "component": getattr(record, "component", "cloudctl"),
                "message": record_msg,
            }
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload)
        return record_msg


_root_logger: logging.Logger | None = None
_file_handler: logging.FileHandler | None = None
_console_handler: logging.StreamHandler | None = None
_formatter: SecretMaskingFormatter | None = None


def setup_logger(
    level: str = "INFO",
    log_file: str | Path | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """Initialize root USPC logger with console and optional file handler."""
    global _root_logger, _file_handler, _console_handler, _formatter

    logger = logging.getLogger("uspc")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    _formatter = SecretMaskingFormatter(
        json_format=json_format,
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setFormatter(_formatter)
    logger.addHandler(_console_handler)

    if log_file:
        p = Path(log_file).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        _file_handler = logging.FileHandler(p, encoding="utf-8")
        _file_handler.setFormatter(_formatter)
        logger.addHandler(_file_handler)

    _root_logger = logger
    return logger


def get_logger(component: str = "cloudctl") -> logging.Logger:
    """Get a component-scoped child logger."""
    global _root_logger
    if _root_logger is None:
        setup_logger()
    return logging.getLogger(f"uspc.{component}")


def register_secret_for_masking(secret: str) -> None:
    """Register a sensitive token or password so it will be automatically masked in all logs."""
    global _formatter
    if _formatter and secret:
        _formatter.add_secret(secret)
