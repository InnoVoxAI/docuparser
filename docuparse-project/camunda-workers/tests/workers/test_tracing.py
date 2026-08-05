from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest
from opentelemetry import propagate, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from workers._tracing import extract_trace_link_from_job, traced_job


def _tracer_with_memory_exporter() -> tuple[trace.Tracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


def _global_memory_exporter() -> InMemorySpanExporter:
    """`traced_job` usa `trace.get_tracer(__name__)` (T037/_tracing.py), que
    delega para o TracerProvider *global* — diferente das outras funções
    deste módulo, que recebem um tracer local por injeção. Não há como
    inspecionar seus spans sem instalar o exporter no provider global."""
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_extract_trace_link_from_job_returns_link_when_traceparent_present() -> None:
    tracer, _ = _tracer_with_memory_exporter()
    carrier: dict[str, str] = {}
    with tracer.start_as_current_span("start-process") as span:
        propagate.inject(carrier)
        expected_trace_id = span.get_span_context().trace_id
        expected_span_id = span.get_span_context().span_id

    job_variables = {"documentId": "doc-1", "traceparent": carrier["traceparent"]}

    link = extract_trace_link_from_job(job_variables)

    assert link is not None
    assert link.context.trace_id == expected_trace_id
    assert link.context.span_id == expected_span_id


def test_extract_trace_link_from_job_returns_none_when_traceparent_absent() -> None:
    link = extract_trace_link_from_job({"documentId": "doc-1"})

    assert link is None


def test_traced_job_marks_span_as_error_when_handler_raises() -> None:
    """T060 (US4) — quando um job handler Zeebe decorado com `@traced_job`
    falha, o span `zeebe.job.{job_type}` correspondente termina com
    status=ERROR e um evento de exceção anexado. Este comportamento já é
    automático via `start_as_current_span` (defaults `record_exception=True`,
    `set_status_on_exception=True`, T037) — nenhum handler chama
    `span.record_exception()` manualmente, e não deveria: nenhum dos seis
    workers (document/ocr/layout/extraction/validation/erp) engole exceções
    antes que o decorator veja a falha."""
    exporter = _global_memory_exporter()

    @traced_job("docuparse-scratch-job")
    async def _failing_job(**kwargs: object) -> None:
        raise ValueError("simulated zeebe job failure")

    async def _call() -> None:
        await _failing_job()

    with pytest.raises(ValueError):
        asyncio.run(_call())

    spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "zeebe.job.docuparse-scratch-job"
    ]
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code == trace.StatusCode.ERROR
    exception_events = [event for event in span.events if event.name == "exception"]
    assert len(exception_events) == 1
    assert exception_events[0].attributes.get("exception.type") == "ValueError"
