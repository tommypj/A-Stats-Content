"""Structured JSON logging configuration."""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)  # LOGGING-02: INFO for production visibility
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
