from __future__ import annotations

import json
from pathlib import Path

import pytest
from events import EVENT_MODELS, validate_event

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "events" / "examples"


def test_known_event_models_cover_required_contracts() -> None:
    assert set(EVENT_MODELS) == {
        "document.received",
        "ocr.completed",
        "ocr.failed",
        "layout.classified",
        "extraction.completed",
        "document.classified",
        "document.condominium_identified",
        "erp.integration.requested",
        "erp.sent",
        "erp.failed",
    }


@pytest.mark.parametrize("example_path", sorted(EXAMPLES_DIR.glob("*.json")))
def test_event_examples_validate(example_path: Path) -> None:
    payload = json.loads(example_path.read_text())
    event = validate_event(payload)
    assert event.event_version == "v1"
    assert event.event_type == payload["event_type"]


def test_document_received_without_source_thread_id_still_validates() -> None:
    """Eventos publicados antes do campo existir continuam válidos."""
    payload = json.loads((EXAMPLES_DIR / "document.received.json").read_text())
    assert payload["data"]["source_thread_id"]
    del payload["data"]["source_thread_id"]

    assert validate_event(payload).data.source_thread_id == ""


def test_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError, match="Unsupported event_type"):
        validate_event({"event_type": "unknown"})
