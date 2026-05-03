from __future__ import annotations

import os

from docuparse_events import LocalJsonlEventBus


def main() -> None:
    root = os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", ".docuparse-events")
    bus = LocalJsonlEventBus(root)
    events = bus.consume("document.received.fake")
    print(f"consumed {len(events)} document.received.fake event(s)")
    for event in events:
        print(event)


if __name__ == "__main__":
    main()
