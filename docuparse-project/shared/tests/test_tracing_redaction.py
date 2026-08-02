from __future__ import annotations

from docuparse_observability.tracing import RedactingSpanProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def _tracer_with_redaction() -> tuple:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    # Ordem importa: a redação precisa rodar antes do processor que exporta
    # (mesma ordem usada por configure_tracing()).
    provider.add_span_processor(RedactingSpanProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


def test_denylisted_attributes_are_removed_before_export() -> None:
    tracer, exporter = _tracer_with_redaction()

    with tracer.start_as_current_span("http request") as span:
        span.set_attribute("http.request.body", "conteúdo extraído do documento...")
        span.set_attribute("http.response.body", '{"raw_text": "texto do documento"}')
        span.set_attribute("Authorization", "Bearer super-secret-token")
        span.set_attribute("api_key_secret", "sensitive-value")
        span.set_attribute("refresh_token", "sensitive-value")
        span.set_attribute("account_password", "sensitive-value")
        span.set_attribute("http.method", "POST")

    (exported,) = exporter.get_finished_spans()

    for denied_key in (
        "http.request.body",
        "http.response.body",
        "Authorization",
        "api_key_secret",
        "refresh_token",
        "account_password",
    ):
        assert denied_key not in exported.attributes

    assert exported.attributes["http.method"] == "POST"


def test_denylist_suffix_matching_is_case_insensitive() -> None:
    tracer, exporter = _tracer_with_redaction()

    with tracer.start_as_current_span("http request") as span:
        span.set_attribute("Client_Secret", "sensitive-value")
        span.set_attribute("AUTHORIZATION", "Bearer sensitive-value")

    (exported,) = exporter.get_finished_spans()

    assert "Client_Secret" not in exported.attributes
    assert "AUTHORIZATION" not in exported.attributes


def test_span_without_denylisted_attributes_is_left_unchanged() -> None:
    tracer, exporter = _tracer_with_redaction()

    with tracer.start_as_current_span("http request") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/api/v1/documents")

    (exported,) = exporter.get_finished_spans()

    assert exported.attributes["http.method"] == "GET"
    assert exported.attributes["http.route"] == "/api/v1/documents"
