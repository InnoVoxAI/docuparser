from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


def configure_json_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(message)s")


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    level: int = logging.INFO,
    tenant_id: str | None = None,
    document_id: str | None = None,
    correlation_id: str | None = None,
    event_type: str | None = None,
    **extra: Any,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "tenant_id": tenant_id,
        "document_id": document_id,
        "correlation_id": correlation_id,
        "event_type": event_type,
        **extra,
    }
    logger.log(level, json.dumps({key: value for key, value in payload.items() if value is not None}, default=str))
