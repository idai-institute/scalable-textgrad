"""Structured logging helpers shared across services."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


def configure_logging(name: str, *, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    extra: Dict[str, Any] = {"event": event, **fields}
    if "message" in extra:
        extra["event_message"] = extra.pop("message")
    logger.info("event", extra=extra)
