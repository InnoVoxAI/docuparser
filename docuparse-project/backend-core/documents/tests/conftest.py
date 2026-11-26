from __future__ import annotations

import os

import pytest
from docuparse_observability.tracing import RedactingSpanProcessor
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider


@pytest.fixture(scope="session")
def sdk_tracer_provider():
    """TracerProvider do SDK com `requests` instrumentado, para os testes de tracing.

    `core/settings.py` só configura tracing e instrumenta `requests` quando
    `USE_TELEMETRY=true`. Com a telemetria desligada (o padrão do `.env` de dev),
    o provider global fica como `ProxyTracerProvider`, que não aceita
    `add_span_processor`, e as chamadas HTTP não geram span. Aqui o provider é
    montado como em `configure_tracing()`, com o `RedactingSpanProcessor` (que
    também normaliza `net.peer.name`), mas sem exporter: cada teste pendura o
    próprio processor (em memória ou para um collector fora do ar) e nada sai
    do processo.
    """
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        # Telemetria ligada: settings.py já montou e instrumentou tudo.
        yield provider
        return

    # Mesmo opt-in de configure_tracing(): sem ele a instrumentação não marca
    # `error.type` no span de saída. Precisa vir antes de instrument().
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http/dup")
    provider = TracerProvider()
    provider.add_span_processor(RedactingSpanProcessor())
    trace.set_tracer_provider(provider)
    instrumentor = RequestsInstrumentor()
    instrumentor.instrument()
    yield provider
    instrumentor.uninstrument()
