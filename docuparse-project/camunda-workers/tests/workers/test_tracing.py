from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from opentelemetry import propagate, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from workers._tracing import extract_trace_link_from_job


def _tracer_with_memory_exporter() -> tuple[trace.Tracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


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
