from __future__ import annotations

from docuparse_events import LocalJsonlEventBus, extract_trace_link
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def _tracer_with_memory_exporter() -> tuple[trace.Tracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


def test_publish_populates_trace_context_when_span_active(tmp_path) -> None:
    tracer, _ = _tracer_with_memory_exporter()
    event_bus = LocalJsonlEventBus(tmp_path)

    with tracer.start_as_current_span("publisher"):
        event_bus.publish("document.received", {"event_type": "document.received"})

    stored = event_bus.consume("document.received")
    assert len(stored) == 1
    assert stored[0]["trace_context"]
    assert "traceparent" in stored[0]["trace_context"]


def test_publish_leaves_trace_context_unset_without_active_span(tmp_path) -> None:
    event_bus = LocalJsonlEventBus(tmp_path)

    event_bus.publish("document.received", {"event_type": "document.received"})

    stored = event_bus.consume("document.received")
    assert stored[0].get("trace_context") is None


def test_extract_trace_link_returns_link_pointing_to_publisher_span(tmp_path) -> None:
    tracer, _ = _tracer_with_memory_exporter()
    event_bus = LocalJsonlEventBus(tmp_path)

    with tracer.start_as_current_span("publisher") as publisher_span:
        event_bus.publish("document.received", {"event_type": "document.received"})
        expected_trace_id = publisher_span.get_span_context().trace_id
        expected_span_id = publisher_span.get_span_context().span_id

    consumed_event = event_bus.consume("document.received")[0]
    link = extract_trace_link(consumed_event)

    assert link is not None
    assert link.context.trace_id == expected_trace_id
    assert link.context.span_id == expected_span_id


def test_extract_trace_link_returns_none_when_trace_context_missing() -> None:
    link = extract_trace_link({"event_type": "document.received"})

    assert link is None
