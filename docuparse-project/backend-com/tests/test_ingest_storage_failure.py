"""US4 (T027/T029) — falha de storage na ingestão aborta de forma explícita e
NÃO publica evento (sem "sucesso silencioso" / documento sem arquivo)."""

from __future__ import annotations

import pytest


def test_storage_write_failure_aborts_without_publishing(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DOCUPARSE_LOCAL_EVENT_DIR", str(tmp_path / "events"))
    from backend_com.services import document_ingest
    from docuparse_events import LocalJsonlEventBus

    document_ingest.settings.local_event_dir = tmp_path / "events"
    document_ingest.settings.backend_core_document_received_url = ""

    class _FailingStorage:
        def put_bytes(self, key, content):  # noqa: ANN001
            raise RuntimeError("storage unavailable")

    # get_storage() passa a devolver um backend que falha na escrita.
    monkeypatch.setattr(document_ingest, "get_storage", lambda *a, **k: _FailingStorage())

    with pytest.raises(RuntimeError):
        document_ingest.ingest_document(
            tenant_id="tenant-demo",
            channel="manual",
            filename="fixture.pdf",
            content_type="application/pdf",
            content=b"%PDF fake",
        )

    # Nenhum evento document.received deve ter sido publicado.
    events = LocalJsonlEventBus(tmp_path / "events").consume("document.received")
    assert events == []
