from __future__ import annotations

import pytest
from docuparse_orchestrator._run_context import current_run_errors, current_run_id
from docuparse_orchestrator.context import orchestration_run
from docuparse_orchestrator.decorators import task


class FakeRunWriter:
    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []
        self.started_document_ids: list[str | None] = []
        self.started_triggered_by: list[str | None] = []
        self.finished: list[tuple[str, str]] = []

    def start(
        self,
        run_id: str,
        name: str,
        *,
        document_id: str | None = None,
        triggered_by: str | None = None,
    ) -> None:
        self.started.append((run_id, name))
        self.started_document_ids.append(document_id)
        self.started_triggered_by.append(triggered_by)

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

    with orchestration_run(
        "document_validation", run_id="fixed-id", writer=writer
    ) as run_id:
        assert run_id == "fixed-id"

    assert writer.started == [("fixed-id", "document_validation")]


def test_orchestration_run_persists_document_id():
    writer = FakeRunWriter()

    with orchestration_run("document_processing", document_id="doc-1", writer=writer):
        pass

    assert writer.started_document_ids == ["doc-1"]


def test_orchestration_run_persists_triggered_by():
    writer = FakeRunWriter()

    with orchestration_run("retry_ocr", triggered_by="operator1", writer=writer):
        pass

    assert writer.started_triggered_by == ["operator1"]


def test_orchestration_run_triggered_by_defaults_to_none():
    writer = FakeRunWriter()

    with orchestration_run("document_processing", writer=writer):
        pass

    assert writer.started_triggered_by == [None]


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


# --- Retomada de run (AR-32) ---------------------------------------------


class ResumableRunWriter(FakeRunWriter):
    def __init__(self) -> None:
        super().__init__()
        self.resumed: list[tuple[str, str]] = []

    def resume(
        self,
        run_id: str,
        name: str,
        *,
        document_id: str | None = None,
        triggered_by: str | None = None,
    ) -> None:
        self.resumed.append((run_id, name))
        self.started_document_ids.append(document_id)
        self.started_triggered_by.append(triggered_by)


def test_resume_reopens_existing_run_instead_of_starting():
    writer = ResumableRunWriter()

    with orchestration_run(
        "document_processing",
        run_id="run-1",
        resume=True,
        document_id="doc-1",
        triggered_by="alice",
        writer=writer,
    ) as run_id:
        assert run_id == "run-1"
        assert current_run_id.get() == "run-1"

    assert writer.started == []
    assert writer.resumed == [("run-1", "document_processing")]
    assert writer.started_document_ids == ["doc-1"]
    assert writer.started_triggered_by == ["alice"]
    assert writer.finished == [("run-1", "COMPLETED")]


def test_resumed_run_tracks_its_own_task_errors():
    """Cada retomada fecha o run pelo resultado dela: uma tentativa que falhou
    não contamina a seguinte."""
    writer = ResumableRunWriter()

    @task("ocr", max_attempts=1, writer=lambda result: None)
    def fails() -> dict:
        raise ValueError("boom")

    with orchestration_run("p", run_id="run-1", resume=True, writer=writer):
        fails()
    with orchestration_run("p", run_id="run-1", resume=True, writer=writer):
        pass

    assert writer.finished == [("run-1", "FAILED"), ("run-1", "COMPLETED")]


def test_resume_requires_run_id():
    with pytest.raises(ValueError):
        with orchestration_run("p", resume=True, writer=ResumableRunWriter()):
            pass


def test_start_failure_does_not_leak_context():
    class BrokenWriter(FakeRunWriter):
        def start(self, *args, **kwargs) -> None:
            raise RuntimeError("db down")

    with pytest.raises(RuntimeError):
        with orchestration_run("p", writer=BrokenWriter()):
            pass

    assert current_run_id.get() is None
    assert current_run_errors.get() is None
