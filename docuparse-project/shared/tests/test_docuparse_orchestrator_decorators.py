from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

import docuparse_orchestrator.decorators as decorators_module
from docuparse_orchestrator.decorators import task


@pytest.fixture()
def in_memory_tracer(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    monkeypatch.setattr(decorators_module, "_tracer", tracer)
    return exporter


@pytest.fixture()
def fake_writer():
    calls: list = []
    return calls, calls.append


def test_task_succeeds_on_first_attempt(in_memory_tracer, fake_writer):
    calls, writer = fake_writer

    @task("greet", writer=writer)
    def greet() -> dict:
        return {"message": "hi"}

    result = greet()

    assert result.status == "ok"
    assert result.payload == {"message": "hi"}
    assert result.attempt == 1
    assert result.duration_ms >= 0
    assert result.run_id
    assert len(calls) == 1
    assert calls[0] is result

    spans = in_memory_tracer.get_finished_spans()
    assert any(span.name == "task.greet" for span in spans)


def test_task_retries_then_succeeds(in_memory_tracer, fake_writer):
    calls, writer = fake_writer
    attempts_made = {"count": 0}

    @task("flaky", max_attempts=3, writer=writer)
    def flaky() -> dict:
        attempts_made["count"] += 1
        if attempts_made["count"] < 2:
            raise ValueError("transient failure")
        return {"ok": True}

    result = flaky()

    assert result.status == "ok"
    assert result.attempt == 2
    assert attempts_made["count"] == 2
    assert len(calls) == 1


def test_task_exhausts_retries_and_returns_error(in_memory_tracer, fake_writer):
    calls, writer = fake_writer

    @task("always_fails", max_attempts=2, writer=writer)
    def always_fails() -> dict:
        raise ValueError("permanent failure")

    result = always_fails()

    assert result.status == "error"
    assert result.attempt == 2
    assert result.error is not None
    assert result.error.type == "ValueError"
    assert result.error.message == "permanent failure"
    assert "ValueError" in result.error.traceback
    assert len(calls) == 1


def test_task_without_active_run_generates_standalone_run_id(in_memory_tracer, fake_writer):
    _, writer = fake_writer

    @task("standalone", writer=writer)
    def standalone() -> dict:
        return {}

    result_a = standalone()
    result_b = standalone()

    assert result_a.run_id
    assert result_b.run_id
    assert result_a.run_id != result_b.run_id
