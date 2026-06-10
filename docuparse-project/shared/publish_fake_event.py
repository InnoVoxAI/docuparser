from __future__ import annotations

import os
from uuid import uuid4

from docuparse_events import LocalJsonlEventBus


def main() -> None:
    root = os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", ".docuparse-events")
    bus = LocalJsonlEventBus(root)
    event = {
        "event_type": "document.received.fake",
        "document_id": str(uuid4()),
        "tenant_id": "tenant-demo",
    }
    offset = bus.publish("document.received.fake", event)
    print(f"published document.received.fake offset={offset} document_id={event['document_id']}")


if __name__ == "__main__":
    main()
