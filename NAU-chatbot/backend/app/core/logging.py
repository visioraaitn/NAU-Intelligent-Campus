from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.file_config import security_file_config


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in ("request_id", "session_id", "event_fields"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


class SecretRedactionFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self.fields = set(security_file_config().redact_log_fields)

    def filter(self, record: logging.LogRecord) -> bool:
        event_fields = getattr(record, "event_fields", None)
        if isinstance(event_fields, dict):
            record.event_fields = {
                key: "[REDACTED]" if key.lower() in self.fields else value
                for key, value in event_fields.items()
            }
        return True


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SecretRedactionFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

