from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.config import Settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)
