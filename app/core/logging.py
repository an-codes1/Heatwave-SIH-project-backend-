"""Lightweight structured application logging.

Log records are emitted as single-line JSON objects with a millisecond
timestamp so they are easy to parse and index. Secrets (database URLs,
Twilio tokens) are never passed to these loggers.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLineFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int | str,
    msg: str,
    **fields: Any,
) -> None:
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.log(level, msg, extra={"extra_fields": fields})