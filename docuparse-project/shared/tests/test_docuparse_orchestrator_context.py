from __future__ import annotations

import pytest

from docuparse_orchestrator._run_context import current_run_errors, current_run_id
from docuparse_orchestrator.context import orchestration_run
from docuparse_orchestrator.decorators import task


class FakeRunWriter:
    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []
        self.finished: list[tuple[str, str]] = []

    def start(self, run_id: str, name: str) -> None:
        self.started.append((run_id, name))

    def finish(self, run_id: str, *, status: str) -> None:
        self.finished.append((run_id, status))


def test_orchestration_run_completes_successfully():
    writer = FakeRunWriter()

    with orchestration_run("document_processing", writer=writer) as run_id:
        assert current_run_id.get() == run_id

    assert writer.started == [(run_id, "document_processing")]
    assert writer.finished == [(run_id, "COMPLETED")]
    assert current_run_id.get() is None


def test_orchestration_run_marks_failed_on_exception():
    writer = FakeRunWriter()

    with pytest.raises(ValueError):
        with orchestration_run("document_processing", writer=writer) as run_id:
            raise ValueError("boom")

    assert writer.finished == [(run_id, "FAILED")]
    assert current_run_id.get() is None


def test_orchestration_run_accepts_explicit_run_id():
    writer = FakeRunWriter()

    with orchestration_run("document_validation", run_id="fixed-id", writer=writer) as run_id:
        assert run_id == "fixed-id"

    assert writer.started == [("fixed-id", "document_validation")]


def test_orchestration_run_marks_failed_when_a_task_errors_without_raising():
    """A @task never raises (decorators.py) — orchestration_run must detect
    the failure on its own via current_run_errors, not rely on the calling
    code re-raising after checking result.status."""
    writer = FakeRunWriter()
    calls: list = []

    @task("always_fails", max_attempts=1, writer=calls.append)
    def always_fails() -> dict:
        raise ValueError("boom")

    with orchestration_run("document_processing", writer=writer) as run_id:
        result = always_fails()
        assert result.status == "error"
        # Orchestrating code does NOT raise/return early here on purpose —
        # this is exactly the "forgot to signal failure" scenario.

    assert writer.finished == [(run_id, "FAILED")]


def test_orchestration_run_resets_error_list_between_runs():
    writer = FakeRunWriter()

    with orchestration_run("run_a", writer=writer):
        current_run_errors.get().append("some-error")

    with orchestration_run("run_b", writer=writer) as run_id:
        assert current_run_errors.get() == []

    assert writer.finished[0][1] == "FAILED"
    assert writer.finished[1] == (run_id, "COMPLETED")
