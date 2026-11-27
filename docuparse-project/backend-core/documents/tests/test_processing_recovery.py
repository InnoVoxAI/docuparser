"""Varredura de documentos e runs parados no processamento em segundo plano."""

from __future__ import annotations

import uuid
from datetime import timedelta
from io import StringIO

from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from orchestrator.models import OrchestrationRun
from tenants.models import Tenant

from documents.models import Document
from documents.services.processing_recovery import (
    STUCK_ERROR_TYPE,
    sweep_stuck_processing,
)

THIRTY_MIN = timedelta(minutes=30)


class SweepStuckProcessingTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-sweep", name="Tenant Sweep")
        connection.set_tenant(self.tenant)
        self.now = timezone.now()
        self.old = self.now - timedelta(hours=2)

    def _document(
        self, *, status=Document.Status.RECEIVED, updated_at=None, metadata=None
    ):
        document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/tenant-sweep/doc/original",
            original_filename="fixture.pdf",
            status=status,
            metadata=metadata or {},
        )
        # updated_at é auto_now: só dá para envelhecer via update().
        Document.objects.filter(id=document.id).update(
            updated_at=updated_at or self.old
        )
        return document

    def _run(self, *, document=None, started_at=None, status=None):
        return OrchestrationRun.objects.create(
            run_id=str(uuid.uuid4()),
            name="document_processing",
            status=status or OrchestrationRun.Status.RUNNING,
            started_at=started_at or self.old,
            document_id=document.id if document else None,
        )

    def test_old_received_document_is_marked_failed(self) -> None:
        document = self._document()

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_document_ids == [str(document.id)]
        document.refresh_from_db()
        assert document.status == Document.Status.OCR_FAILED
        assert document.metadata["processing_error"]["error_type"] == STUCK_ERROR_TYPE
        assert "30 min" in document.metadata["processing_error"]["error"]

    def test_recent_received_document_is_left_alone(self) -> None:
        document = self._document(updated_at=self.now - timedelta(minutes=5))

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_document_ids == []
        document.refresh_from_db()
        assert document.status == Document.Status.RECEIVED

    def test_document_with_recent_running_run_is_still_processing(self) -> None:
        document = self._document()
        run = self._run(document=document, started_at=self.now - timedelta(minutes=2))

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result == type(result)()
        document.refresh_from_db()
        run.refresh_from_db()
        assert document.status == Document.Status.RECEIVED
        assert run.status == OrchestrationRun.Status.RUNNING

    def test_stale_running_run_is_closed_and_its_document_marked_failed(self) -> None:
        document = self._document()
        run = self._run(document=document)

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stale_run_ids == [run.run_id]
        assert result.stuck_document_ids == [str(document.id)]
        run.refresh_from_db()
        assert run.status == OrchestrationRun.Status.FAILED
        assert run.finished_at == self.now
        document.refresh_from_db()
        assert document.status == Document.Status.OCR_FAILED

    def test_documents_past_received_are_never_touched(self) -> None:
        document = self._document(status=Document.Status.VALIDATION_PENDING)

        sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        document.refresh_from_db()
        assert document.status == Document.Status.VALIDATION_PENDING

    def test_finished_runs_are_never_touched(self) -> None:
        run = self._run(status=OrchestrationRun.Status.COMPLETED)

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stale_run_ids == []
        run.refresh_from_db()
        assert run.status == OrchestrationRun.Status.COMPLETED

    def test_dry_run_reports_without_changing_anything(self) -> None:
        document = self._document()
        run = self._run(document=document)

        result = sweep_stuck_processing(
            older_than=THIRTY_MIN, now=self.now, dry_run=True
        )

        assert result.stale_run_ids == [run.run_id]
        assert result.stuck_document_ids == [str(document.id)]
        document.refresh_from_db()
        run.refresh_from_db()
        assert document.status == Document.Status.RECEIVED
        assert run.status == OrchestrationRun.Status.RUNNING

    def _extraction_running(self, *, status=Document.Status.OCR_COMPLETED, **kwargs):
        return self._document(
            status=status,
            metadata={
                "extraction": {
                    "state": "running",
                    "schema_id": "boleto_v1",
                    "trigger": "auto",
                    "updated_at": self.old.isoformat(),
                }
            },
            **kwargs,
        )

    def test_stuck_auto_extraction_is_marked_failed_keeping_status(self) -> None:
        document = self._extraction_running()

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_extraction_ids == [str(document.id)]
        assert result.stuck_document_ids == []
        document.refresh_from_db()
        assert document.status == Document.Status.OCR_COMPLETED
        extraction = document.metadata["extraction"]
        assert extraction["state"] == "failed"
        assert extraction["error_type"] == STUCK_ERROR_TYPE
        assert "30 min" in extraction["error"]
        # Preserva o contexto gravado pela extração.
        assert extraction["schema_id"] == "boleto_v1"
        assert extraction["trigger"] == "auto"

    def test_stuck_manual_extraction_in_any_status_is_marked_failed(self) -> None:
        document = self._extraction_running(status=Document.Status.VALIDATION_PENDING)

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_extraction_ids == [str(document.id)]
        document.refresh_from_db()
        assert document.status == Document.Status.VALIDATION_PENDING
        assert document.metadata["extraction"]["state"] == "failed"

    def test_recent_running_extraction_is_left_alone(self) -> None:
        document = self._extraction_running(updated_at=self.now - timedelta(minutes=5))

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_extraction_ids == []
        document.refresh_from_db()
        assert document.metadata["extraction"]["state"] == "running"

    def test_extraction_with_recent_running_run_is_still_processing(self) -> None:
        document = self._extraction_running()
        self._run(document=document, started_at=self.now - timedelta(minutes=2))

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_extraction_ids == []
        document.refresh_from_db()
        assert document.metadata["extraction"]["state"] == "running"

    def test_stale_retry_run_is_closed_with_its_stuck_extraction(self) -> None:
        document = self._extraction_running()
        run = OrchestrationRun.objects.create(
            run_id=str(uuid.uuid4()),
            name="retry_extraction",
            status=OrchestrationRun.Status.RUNNING,
            started_at=self.old,
            document_id=document.id,
        )

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stale_run_ids == [run.run_id]
        assert result.stuck_extraction_ids == [str(document.id)]
        run.refresh_from_db()
        assert run.status == OrchestrationRun.Status.FAILED

    def test_finished_or_absent_extraction_is_never_touched(self) -> None:
        # OCR_COMPLETED sem extração é legítimo (auto-extração desligada).
        no_extraction = self._document(status=Document.Status.OCR_COMPLETED)
        failed = self._document(
            status=Document.Status.OCR_COMPLETED,
            metadata={"extraction": {"state": "failed", "error": "boom"}},
        )

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert result.stuck_extraction_ids == []
        no_extraction.refresh_from_db()
        failed.refresh_from_db()
        assert no_extraction.metadata == {}
        assert failed.metadata["extraction"] == {"state": "failed", "error": "boom"}

    def test_erp_integration_requested_is_never_touched(self) -> None:
        # SuperlogicaMode.DISABLED deixa o documento aqui de propósito.
        document = self._document(status=Document.Status.ERP_INTEGRATION_REQUESTED)

        result = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert not result.changed
        document.refresh_from_db()
        assert document.status == Document.Status.ERP_INTEGRATION_REQUESTED

    def test_dry_run_does_not_touch_stuck_extraction(self) -> None:
        document = self._extraction_running()

        result = sweep_stuck_processing(
            older_than=THIRTY_MIN, now=self.now, dry_run=True
        )

        assert result.stuck_extraction_ids == [str(document.id)]
        document.refresh_from_db()
        assert document.metadata["extraction"]["state"] == "running"

    def test_sweep_is_idempotent(self) -> None:
        self._document()
        self._extraction_running()
        self._run()

        first = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)
        second = sweep_stuck_processing(older_than=THIRTY_MIN, now=self.now)

        assert first.changed
        assert not second.changed


class SweepStuckDocumentsCommandTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-sweep-cmd", name="Sweep Cmd")
        connection.set_tenant(self.tenant)
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/tenant-sweep-cmd/doc/original",
            original_filename="fixture.pdf",
        )
        Document.objects.filter(id=self.document.id).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )

    def test_command_sweeps_the_tenant_schema(self) -> None:
        output = StringIO()

        call_command(
            "sweep_stuck_documents", "--tenant", self.tenant.slug, stdout=output
        )

        assert (
            "tenant-sweep-cmd: 0 run(s) fechados, 1 documento(s) marcados como "
            "falhos, 0 extração(ões)" in output.getvalue()
        )
        connection.set_tenant(self.tenant)
        self.document.refresh_from_db()
        assert self.document.status == Document.Status.OCR_FAILED

    def test_command_dry_run_changes_nothing(self) -> None:
        output = StringIO()

        call_command(
            "sweep_stuck_documents",
            "--tenant",
            self.tenant.slug,
            "--dry-run",
            stdout=output,
        )

        assert output.getvalue().startswith("[dry-run] tenant-sweep-cmd")
        connection.set_tenant(self.tenant)
        self.document.refresh_from_db()
        assert self.document.status == Document.Status.RECEIVED

    def test_command_reports_stuck_extraction(self) -> None:
        connection.set_tenant(self.tenant)
        stuck = Document.objects.create(
            channel="manual",
            file_uri="local://documents/tenant-sweep-cmd/doc2/original",
            original_filename="fixture2.pdf",
            status=Document.Status.OCR_COMPLETED,
            metadata={"extraction": {"state": "running"}},
        )
        Document.objects.filter(id=stuck.id).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        output = StringIO()

        call_command(
            "sweep_stuck_documents", "--tenant", self.tenant.slug, stdout=output
        )

        assert "1 extração(ões) marcadas como falhas" in output.getvalue()
        assert f"extração {stuck.id}" in output.getvalue()
        connection.set_tenant(self.tenant)
        stuck.refresh_from_db()
        assert stuck.metadata["extraction"]["state"] == "failed"

    def test_unknown_tenant_is_an_error(self) -> None:
        with self.assertRaises(CommandError):
            call_command("sweep_stuck_documents", "--tenant", "nao-existe")
