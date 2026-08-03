"""Local observability helpers with sensitive-value redaction."""
from __future__ import annotations

import logging
import re
from collections.abc import Mapping

LOGGER_NAME = "tekla_nest.ui"

_SENSITIVE_PATTERNS = [
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
    re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    ),
    re.compile(r"(?i)(license[_ -]?key|machine[_ -]?id)\s*[:=]\s*\S+"),
]


def redact(value: object) -> str:
    """Return a log-safe string without license keys or machine IDs."""
    text = str(value)
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def redacted_fields(fields: Mapping[str, object]) -> dict[str, str]:
    return {key: redact(value) for key, value in fields.items()}


def get_ui_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def log_ui_event(event: str, operation: str, **fields: object) -> None:
    """Log a non-sensitive UI lifecycle event."""
    payload = redacted_fields(fields)
    payload_text = " ".join(f"{key}={value}" for key, value in payload.items())
    message = f"event={event} operation={operation}"
    if payload_text:
        message = f"{message} {payload_text}"
    get_ui_logger().info(message)
