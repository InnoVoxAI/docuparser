"""Traduz o resultado do conector em eventos `erp.sent` e `erp.failed`.

Os consumidores que já existem (`consume_erp_sent` e `consume_erp_failed`) atualizam a
tentativa e o status do documento; este módulo só publica o evento certo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from django.conf import settings
from docuparse_events import event_bus_from_env
from events import ERPFailedEvent, ERPIntegrationRequestedEvent, ERPSentEvent

from erp_export.connector import ConnectorResult

logger = logging.getLogger(__name__)

SOURCE = "erp-superlogica"


def _base(request: ERPIntegrationRequestedEvent) -> dict[str, Any]:
    return {
        "event_id": uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "tenant_id": request.tenant_id,
        "document_id": request.document_id,
        "correlation_id": request.correlation_id,
        "source": SOURCE,
    }


def build_outcome_event(
    request: ERPIntegrationRequestedEvent, result: ConnectorResult
) -> tuple[str, dict[str, Any]] | None:
    """(stream, evento) a publicar; None quando não há nada a informar."""
    connector = request.data.connector
    key = request.data.idempotency_key
    if result.kind == "sent":
        event = ERPSentEvent(
            **_base(request),
            data={
                "connector": connector,
                "external_id": result.external_id,
                "idempotency_key": key,
                "response_metadata": {"reconciled": result.reconciled},
            },
        )
        return "erp.sent", event.model_dump(mode="json")
    if result.kind == "failed" and result.error is not None:
        error = result.error
        metadata: dict[str, Any] = {
            "code": error.code,
            "outcome_unknown": error.outcome_unknown,
        }
        if result.detail.get("errors"):
            metadata["errors"] = result.detail["errors"]
        event = ERPFailedEvent(
            **_base(request),
            data={
                "connector": connector,
                "reason": error.message,
                "retryable": error.retryable,
                "idempotency_key": key,
                "response_metadata": metadata,
            },
        )
        return "erp.failed", event.model_dump(mode="json")
    return None


def apply_outcome(stream: str, event: dict[str, Any]) -> None:
    """Grava o resultado no banco do tenant atual (tentativa e status do documento)."""
    from documents.services.event_consumers import consume_erp_failed, consume_erp_sent

    {"erp.sent": consume_erp_sent, "erp.failed": consume_erp_failed}[stream](event)


def publish_outcome(
    request: ERPIntegrationRequestedEvent, result: ConnectorResult
) -> None:
    """Publica o resultado no barramento e o aplica direto no banco.

    O banco é a fonte da verdade: se o barramento estiver fora, o resultado é gravado
    do mesmo jeito. Um worker de eventos que também consuma `erp.sent`/`erp.failed`
    não duplica nada, porque os consumidores ignoram evento já registrado.
    """
    built = build_outcome_event(request, result)
    if built is None:
        return
    stream, event = built
    try:
        event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR).publish(stream, event)
    except Exception:
        logger.warning("erp_outcome_bus_publish_failed stream=%s", stream)
    apply_outcome(stream, event)
