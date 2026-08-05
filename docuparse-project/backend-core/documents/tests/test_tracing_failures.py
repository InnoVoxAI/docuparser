from __future__ import annotations

import io
import socket

import pytest
from documents.services.langextract_client import LangExtractClient
from documents.services.ocr_client import OCRClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


@pytest.fixture
def unreachable_url() -> str:
    """Bind then immediately close a port so the connection is refused —
    stands in for backend-ocr/langextract-service being temporarily down
    (T048/US3 independent test: 'forçar indisponibilidade temporária')."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def memory_span_exporter():
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter
    exporter.clear()


def _outgoing_client_span(exporter: InMemorySpanExporter):
    client_spans = [
        span
        for span in exporter.get_finished_spans()
        if span.kind == trace.SpanKind.CLIENT
    ]
    assert client_spans, "expected an outgoing HTTP client span"
    return client_spans[0]


def test_ocr_client_failure_produces_error_span_with_destination_and_error_type(
    unreachable_url, memory_span_exporter, settings
) -> None:
    """T048 — chamada de documents/services/ocr_client.py para um
    backend-ocr indisponível produz um span de saída com status=ERROR,
    atributo identificando o destino (net.peer.name) e error.type
    identificando a natureza da falha (conexão recusada)."""
    settings.BACKEND_OCR_URL = unreachable_url

    with pytest.raises(Exception):
        OCRClient().process_document(io.BytesIO(b"fake-pdf-bytes"), "fixture.pdf")

    span = _outgoing_client_span(memory_span_exporter)
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes.get("net.peer.name") == "127.0.0.1"
    assert span.attributes.get("error.type")


def test_langextract_client_failure_produces_error_span_with_destination_and_error_type(
    unreachable_url, memory_span_exporter, settings
) -> None:
    """T048 — mesmo comportamento para documents/services/langextract_client.py
    quando langextract-service está indisponível."""
    settings.LANGEXTRACT_SERVICE_URL = unreachable_url

    with pytest.raises(Exception):
        LangExtractClient().extract_with_schema("texto", {})

    span = _outgoing_client_span(memory_span_exporter)
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes.get("net.peer.name") == "127.0.0.1"
    assert span.attributes.get("error.type")
