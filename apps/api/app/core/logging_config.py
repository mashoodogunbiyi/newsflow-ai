"""Safe structured application logging configuration."""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

_HANDLER_NAME = "newsflow-structured"
_STRUCTURED_FIELDS = {
    "attempt",
    "counts",
    "delay_seconds",
    "duration_ms",
    "error_category",
    "error_code",
    "event",
    "failed_stage",
    "health_status",
    "job_id",
    "model",
    "provider_duration_ms",
    "provider_id",
    "request_id",
    "status",
    "trigger_type",
}
_URI_CREDENTIALS = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)[^:@/\s]+:[^@/\s]+@",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret|token)\b\s*[:=]\s*[^\s,;]+"
)
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def redact_sensitive_text(value: str) -> str:
    """Redact common credential shapes before any message is emitted."""

    redacted = _URI_CREDENTIALS.sub(r"\g<scheme>***:***@", value)
    redacted = _SECRET_ASSIGNMENT.sub(r"\1=[REDACTED]", redacted)
    return _OPENAI_KEY.sub("[REDACTED]", redacted)


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return value


class StructuredJsonFormatter(logging.Formatter):
    """Render allowlisted operational fields as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": redact_sensitive_text(record.getMessage()),
        }
        for field_name in _STRUCTURED_FIELDS:
            if hasattr(record, field_name):
                payload[field_name] = _safe_value(getattr(record, field_name))
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class StructuredConsoleFormatter(logging.Formatter):
    """Readable local format that preserves the same structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        fields = []
        for field_name in sorted(_STRUCTURED_FIELDS):
            if hasattr(record, field_name):
                value = _safe_value(getattr(record, field_name))
                fields.append(f"{field_name}={value}")
        suffix = f" {' '.join(fields)}" if fields else ""
        return (
            f"{record.levelname.lower()} {record.name} "
            f"{redact_sensitive_text(record.getMessage())}{suffix}"
        )


def configure_logging(*, level: str, log_format: str) -> None:
    """Install one reusable NewsFlow handler without removing test handlers."""

    root = logging.getLogger()
    handler = next(
        (
            item
            for item in root.handlers
            if getattr(item, "name", None) == _HANDLER_NAME
        ),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler.name = _HANDLER_NAME
        root.addHandler(handler)
    handler.setFormatter(
        StructuredJsonFormatter()
        if log_format == "json"
        else StructuredConsoleFormatter()
    )
    root.setLevel(getattr(logging, level.upper()))


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Emit a named event with only explicitly allowlisted safe fields."""

    safe_fields = {
        name: _safe_value(value)
        for name, value in fields.items()
        if name in _STRUCTURED_FIELDS and value is not None
    }
    safe_fields["event"] = event
    logger.log(level, event, extra=safe_fields)
