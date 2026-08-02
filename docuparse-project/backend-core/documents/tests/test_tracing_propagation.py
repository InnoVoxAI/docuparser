from __future__ import annotations

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from documents.services.ocr_client import OCRClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class _FakeOCRHandler(BaseHTTPRequestHandler):
    """Standin for backend-ocr's /api/v1/process — records incoming headers."""

    received_headers: list[dict[str, str]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        type(self).received_headers.append(dict(self.headers.items()))
        body = json.dumps(
            {"raw_text": "ok", "document_type": "digital_pdf", "engine_used": "mock"}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


@pytest.fixture
def fake_ocr_server():
    _FakeOCRHandler.received_headers = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOCRHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, _FakeOCRHandler
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture
def memory_span_exporter():
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter
    exporter.clear()


def test_ocr_client_call_propagates_traceparent_and_creates_child_span(
    fake_ocr_server, memory_span_exporter, settings
) -> None:
    """T029 — chamada de documents/services/ocr_client.py para backend-ocr
    propaga `traceparent` e produz um span filho corretamente contextualizado."""
    server, handler_cls = fake_ocr_server
    settings.BACKEND_OCR_URL = f"http://127.0.0.1:{server.server_address[1]}"

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("inbound-request") as parent_span:
        expected_trace_id = parent_span.get_span_context().trace_id
        expected_parent_span_id = parent_span.get_span_context().span_id
        OCRClient().process_document(io.BytesIO(b"fake-pdf-bytes"), "fixture.pdf")

    assert len(handler_cls.received_headers) == 1
    traceparent = handler_cls.received_headers[0].get("traceparent")
    assert traceparent is not None
    propagated_trace_id = int(traceparent.split("-")[1], 16)
    assert propagated_trace_id == expected_trace_id

    client_spans = [
        span
        for span in memory_span_exporter.get_finished_spans()
        if span.kind == trace.SpanKind.CLIENT
    ]
    assert client_spans, "expected an outgoing HTTP client span from RequestsInstrumentor"
    outgoing_span = client_spans[0]
    assert outgoing_span.context.trace_id == expected_trace_id
    assert outgoing_span.parent is not None
    assert outgoing_span.parent.span_id == expected_parent_span_id
    assert outgoing_span.end_time > outgoing_span.start_time
