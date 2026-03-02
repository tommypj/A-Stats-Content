"""Structured JSON logging configuration."""

import json
import logging
import re
import sys
from datetime import UTC, datetime

# LOW-13: Patterns that may contain secrets or credentials — redacted before any log output
_SENSITIVE_PATTERNS = [
    (re.compile(r"(Authorization:\s*Bearer\s+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'(api[_-]?key["\s:=]+)[^\s&"\']+', re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'(password["\s:=]+)[^\s&"\']+', re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'(secret["\s:=]+)[^\s&"\']+', re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
]


def _redact(value: str) -> str:
    """Apply all sensitive-data patterns to a string and return the redacted result."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


class SensitiveDataFilter(logging.Filter):
    """Redacts Bearer tokens, API keys, passwords, and secrets from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            try:
                if isinstance(record.args, tuple):
                    record.args = tuple(
                        _redact(a) if isinstance(a, str) else a for a in record.args
                    )
                elif isinstance(record.args, dict):
                    record.args = {
                        k: (_redact(v) if isinstance(v, str) else v) for k, v in record.args.items()
                    }
            except Exception:
                pass
        return True


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "user_id"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # LOGGING-01: Wrap JSON serialization in try/except to handle non-serializable extra fields
        try:
            return json.dumps(log_entry, default=str)
        except TypeError:
            return str(log_entry)


def setup_logging(json_output: bool = False, level: str = "INFO") -> None:
    """
    Configure root logger.

    Args:
        json_output: If True, use JSON formatter (for production).
                     If False, use standard human-readable format (for development).
        level: Log level string.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    # LOW-13: Attach the sensitive-data filter so all log records are scrubbed
    sensitive_filter = SensitiveDataFilter()
    root.addFilter(sensitive_filter)

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO
    )  # LOGGING-02: INFO for production visibility
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
