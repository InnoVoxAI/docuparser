"""Pool de processamento em segundo plano: conexão com o banco e falhas.

Regressão do incidente em hml (11/2026): após um restart do Postgres, as threads
do pool continuavam com a conexão morta, toda tarefa falhava ao gravar o run e
a exceção sumia dentro do Future — documentos parados sem nenhum log.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from django.db import OperationalError, connection
from django.test import SimpleTestCase, TestCase
from docuparse_orchestrator.persistence import default_django_run_writer
from tenants.models import Tenant

from documents.models import Document
from documents.services import processing_queue

MODULE = "documents.services.processing_queue"


class WithFreshConnectionTests(SimpleTestCase):
    def test_renews_connection_before_and_closes_after_task(self) -> None:
        events = MagicMock()
        with (
            patch(f"{MODULE}.close_old_connections", events.close_old),
            patch(f"{MODULE}.connection") as conn,
        ):
            conn.close = events.close
            processing_queue._with_fresh_connection(events.task, 1, "x")

        assert events.mock_calls == [call.close_old(), call.task(1, "x"), call.close()]

    def test_closes_connection_even_when_task_raises(self) -> None:
        task = MagicMock(side_effect=RuntimeError("boom"))
        with (
            patch(f"{MODULE}.close_old_connections"),
            patch(f"{MODULE}.connection") as conn,
        ):
            with self.assertRaises(RuntimeError):
                processing_queue._with_fresh_connection(task)

        conn.close.assert_called_once_with()


class SubmitTests(SimpleTestCase):
    def test_document_processing_runs_inside_fresh_connection_wrapper(self) -> None:
        tenant = MagicMock(slug="t")
        with (
            patch(f"{MODULE}._tenant_from_connection", return_value=tenant),
            patch(f"{MODULE}.capture_current_span_link", return_value=None),
            patch(f"{MODULE}._executor") as executor,
        ):
            processing_queue.submit_document_processing(42)

        executor.submit.assert_called_once_with(
            processing_queue._with_fresh_connection,
            processing_queue._run_document_processing_safely,
            42,
            tenant,
            None,
        )

    def test_langextract_runs_inside_fresh_connection_wrapper(self) -> None:
        tenant = MagicMock(slug="t")
        with (
            patch(f"{MODULE}._tenant_from_connection", return_value=tenant),
            patch(f"{MODULE}.capture_current_span_link", return_value=None),
            patch(f"{MODULE}._executor") as executor,
        ):
            processing_queue.submit_document_langextract(42, 7)

        executor.submit.assert_called_once_with(
            processing_queue._with_fresh_connection,
            processing_queue._run_langextract_safely,
            42,
            7,
            tenant,
            None,
        )


class RunDocumentProcessingSafelyTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-queue", name="Tenant Queue")
        connection.set_tenant(self.tenant)
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/tenant-queue/doc/original",
            original_filename="fixture.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )
        # Dentro do TestCase a conexão está numa transação: fechá-la quebraria o
        # teste. A troca de conexão é coberta em WithFreshConnectionTests.
        patcher = patch(f"{MODULE}.close_old_connections")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dead_connection_when_opening_run_is_logged_and_marks_document_failed(
        self,
    ) -> None:
        # Mesmo ponto onde falhava em hml: a gravação do run, antes do OCR.
        with (
            patch.object(
                default_django_run_writer,
                "start",
                side_effect=OperationalError("server closed the connection"),
            ),
            self.assertLogs(MODULE, level="ERROR") as logs,
        ):
            processing_queue._run_document_processing_safely(
                self.document.id, self.tenant, None
            )

        assert len(logs.records) == 1
        record = logs.records[0]
        assert "processing_queue_failed" in record.getMessage()
        assert "last_step=not_started" in record.getMessage()
        assert "OperationalError" in record.getMessage()
        assert record.exc_info is not None

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.OCR_FAILED
        assert self.document.metadata["processing_error"] == {
            "error_type": "OperationalError",
            "error": "server closed the connection",
        }

    def test_does_not_overwrite_document_that_already_advanced(self) -> None:
        self.document.transition_to(Document.Status.VALIDATION_PENDING)
        with (
            patch(
                f"{MODULE}._run_document_processing",
                side_effect=RuntimeError("falha depois da extração"),
            ),
            self.assertLogs(MODULE, level="ERROR"),
        ):
            processing_queue._run_document_processing_safely(
                self.document.id, self.tenant, None
            )

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.VALIDATION_PENDING
        assert "processing_error" not in self.document.metadata

    def test_failure_to_mark_document_is_logged_not_raised(self) -> None:
        with (
            patch(
                f"{MODULE}._run_document_processing",
                side_effect=OperationalError("primeira falha"),
            ),
            patch.object(
                Document.objects, "filter", side_effect=OperationalError("banco fora")
            ),
            self.assertLogs(MODULE, level="ERROR") as logs,
        ):
            processing_queue._run_document_processing_safely(
                self.document.id, self.tenant, None
            )

        messages = [r.getMessage() for r in logs.records]
        assert any("processing_queue_failed" in m for m in messages)
        assert any("processing_queue_mark_failed_error" in m for m in messages)

    def test_last_step_is_reset_between_tasks_of_the_same_thread(self) -> None:
        from documents.services import ocr_processor

        ocr_processor._progress.step = "ocr_request"  # resto da tarefa anterior
        with (
            patch(
                f"{MODULE}._run_document_processing",
                side_effect=RuntimeError("x"),
            ),
            self.assertLogs(MODULE, level="ERROR") as logs,
        ):
            processing_queue._run_document_processing_safely(
                self.document.id, self.tenant, None
            )

        assert "last_step=not_started" in logs.records[0].getMessage()
