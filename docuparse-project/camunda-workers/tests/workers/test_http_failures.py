from __future__ import annotations

import asyncio
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest
from config import settings
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from docuparse_observability.tracing import RedactingSpanProcessor
from workers import _http


def _unreachable_url() -> str:
    """Bind then immediately close a port so the connection is refused —
    stands in for one of the services called by camunda-workers being
    temporarily down (T049/US3)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def instrumented_httpx():
    # `error.type` só é emitido pela instrumentação httpx com o semconv HTTP
    # "novo" ativo — mesmo ajuste feito em configure_tracing() (T050); aqui
    # precisa ser setado antes do primeiro `.instrument()` do processo de
    # teste, já que o valor é lido e cacheado uma única vez por processo.
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http/dup")

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(RedactingSpanProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    instrumentor = HTTPXClientInstrumentor()
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    instrumentor.instrument(tracer_provider=provider)
    try:
        yield exporter
    finally:
        instrumentor.uninstrument()


@pytest.mark.parametrize(
    "client_factory, url_attr",
    [
        (_http.core_client, "backend_core_url"),
        (_http.ocr_client, "backend_ocr_url"),
        (_http.layout_client, "layout_service_url"),
        (_http.langextract_client, "langextract_service_url"),
    ],
)
def test_http_client_failure_produces_error_span_with_destination_and_error_type(
    client_factory, url_attr, instrumented_httpx, monkeypatch
) -> None:
    """T049 — falha de um dos clients HTTP de src/workers/_http.py produz um
    span de saída com status=ERROR, origem/destino identificados
    (net.peer.name) e error.type identificando a natureza da falha."""
    monkeypatch.setattr(settings, url_attr, _unreachable_url())

    async def _call() -> None:
        async with client_factory(timeout=1.0) as client:
            await client.get("/health")

    with pytest.raises(Exception):
        asyncio.run(_call())

    client_spans = [
        span
        for span in instrumented_httpx.get_finished_spans()
        if span.kind == trace.SpanKind.CLIENT
    ]
    assert client_spans, "expected an outgoing HTTP client span"
    span = client_spans[0]
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes.get("net.peer.name") == "127.0.0.1"
    assert span.attributes.get("error.type")
