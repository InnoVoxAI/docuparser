from __future__ import annotations

import io
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from documents.services.ocr_client import OCRClient
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Mesmo timeout de exportação usado por
# shared/docuparse_observability/tracing.py::configure_tracing(). Se a
# requisição de teste levasse algo na mesma ordem de grandeza deste valor,
# seria sinal de que a exportação (que deveria ser assíncrona) está
# bloqueando o caminho de resposta ao usuário — violando FR-008.
_EXPORT_TIMEOUT_SECONDS = 2


class _FakeOCRHandler(BaseHTTPRequestHandler):
    """Standin rápido para backend-ocr's /api/v1/process."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = (
            b'{"raw_text": "ok", "document_type": "digital_pdf", '
            b'"engine_used": "mock"}'
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


@pytest.fixture
def fake_ocr_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOCRHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture
def unreachable_collector_span_processor():
    """T064 (FR-008) — simula o Collector fora do ar: registra um segundo
    BatchSpanProcessor no TracerProvider já ativo, exportando para um
    endpoint que recusa conexão (porta ligada e fechada, mesma técnica de
    determinismo usada em test_tracing_failures.py). Como BatchSpanProcessor
    exporta em thread separada, a falha de exportação não deve propagar
    nem atrasar o caminho de resposta ao usuário."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    exporter = OTLPSpanExporter(
        endpoint=f"http://127.0.0.1:{port}", timeout=_EXPORT_TIMEOUT_SECONDS
    )
    processor = BatchSpanProcessor(
        exporter, export_timeout_millis=_EXPORT_TIMEOUT_SECONDS * 1000
    )
    provider = trace.get_tracer_provider()
    provider.add_span_processor(processor)
    yield
    processor.shutdown()


def test_request_completes_normally_when_collector_is_unreachable(
    fake_ocr_server, unreachable_collector_span_processor, settings
) -> None:
    """T064/FR-008 — com o exporter apontando para um endpoint inalcançável,
    uma requisição que atravessa código instrumentado completa normalmente,
    sem erro e sem aumento perceptível de latência (a exportação falha em
    background, nunca no caminho da resposta)."""
    settings.BACKEND_OCR_URL = f"http://127.0.0.1:{fake_ocr_server.server_address[1]}"

    started = time.monotonic()
    result = OCRClient().process_document(io.BytesIO(b"fake-pdf-bytes"), "fixture.pdf")
    elapsed = time.monotonic() - started

    assert result == {
        "raw_text": "ok",
        "document_type": "digital_pdf",
        "engine_used": "mock",
    }
    # Bem abaixo do timeout de exportação (2s) — se a exportação estivesse
    # bloqueando o caminho de resposta, o teste levaria >= _EXPORT_TIMEOUT_SECONDS.
    assert elapsed < 1.0, (
        f"request took {elapsed:.3f}s — exporter pointed at an unreachable "
        "Collector appears to be blocking the response path (violates FR-008)"
    )
