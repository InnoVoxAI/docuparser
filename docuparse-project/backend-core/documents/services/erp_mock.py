from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from events import ERPIntegrationRequestedEvent, ERPSentEvent


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int:
        ...


def handle_erp_integration_requested_event(
    payload: dict[str, Any],
    publisher: EventPublisher,
    *,
    source: str = "erp-mock",
) -> dict[str, Any]:
    event = ERPIntegrationRequestedEvent.model_validate(payload)
    output = ERPSentEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        tenant_id=event.tenant_id,
        document_id=event.document_id,
        correlation_id=event.correlation_id,
        source=source,
        data={
            "connector": event.data.connector,
            "external_id": f"mock-{event.document_id}",
            "idempotency_key": event.data.idempotency_key,
            "response_metadata": {
                "mock": True,
                "request_event_id": str(event.event_id),
            },
        },
    ).model_dump(mode="json")
    publisher.publish("erp.sent", output)
    return output
