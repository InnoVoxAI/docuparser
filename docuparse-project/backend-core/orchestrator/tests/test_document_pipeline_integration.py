from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from docuparse_orchestrator.context import orchestration_run
from docuparse_storage import LocalStorage, document_original_key
from tenants.models import Tenant

from documents.models import Document, LayoutConfig, SchemaConfig, ValidationDecision
from documents.services.processing_queue import _run_document_processing
from documents.views import validation_decision_task
from orchestrator.models import OrchestrationRun, TaskExecution


class DocumentPipelineIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(
            slug="tenant-orchestrator-e2e", name="Tenant Orchestrator E2E"
        )
        connection.set_tenant(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="operator", password="test"
        )

        schema = SchemaConfig.objects.create(
            schema_id="boleto", version="v1", definition={"fields": ["valor"]}
        )
        LayoutConfig.objects.create(
            layout="boleto_padrao", document_type="", schema_config=schema
        )

        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://placeholder",
            original_filename="fixture.pdf",
            content_type="application/pdf",
            size_bytes=10,
            layout="boleto_padrao",
        )

    def _store_original_file(self, storage_dir: str) -> None:
        stored = LocalStorage(storage_dir).put_bytes(
            document_original_key(self.tenant.slug, str(self.document.id)),
            b"%PDF fixture",
        )
        self.document.file_uri = stored.uri
        self.document.save(update_fields=["file_uri"])

    def test_processing_and_validation_produce_full_task_history(self) -> None:
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            patch.dict(os.environ, {"DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir}),
            self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            self._store_original_file(storage_dir)

            with (
                patch("documents.services.ocr_processor.OCRClient") as ocr_client_class,
                patch(
                    "documents.services.ocr_processor.LangExtractClient"
                ) as langextract_class,
            ):
                ocr_client_class.return_value.process_document.return_value = {
                    "raw_text": "valor R$ 123,45",
                    "document_type": "digital_pdf",
                    "engine_used": "mock",
                }
                langextract_class.return_value.extract_with_schema.return_value = {
                    "fields": {"valor": "R$ 123,45"},
                    "confidence": 0.9,
                    "requires_human_validation": True,
                }

                _run_document_processing(self.document.id, self.tenant, None)

        processing_run = OrchestrationRun.objects.get(name="document_processing")
        assert processing_run.status == OrchestrationRun.Status.COMPLETED
        processing_tasks = list(
            processing_run.task_executions.order_by("created_at").values_list(
                "task_name", "status"
            )
        )
        assert processing_tasks == [("ocr", "OK"), ("extraction", "OK")]

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.VALIDATION_PENDING

        with orchestration_run("document_validation") as run_id:
            result = validation_decision_task(
                self.document.id,
                ValidationDecision.Decision.APPROVED,
                "",
                {},
                self.user.id,
            )

        assert result.status == "ok"
        validation_run = OrchestrationRun.objects.get(run_id=run_id)
        assert validation_run.status == OrchestrationRun.Status.COMPLETED
        validation_tasks = list(validation_run.task_executions.all())
        assert len(validation_tasks) == 1
        assert validation_tasks[0].task_name == "validation_decision"

        assert TaskExecution.objects.count() == 3

    def test_ocr_failure_retries_skips_extraction_and_marks_run_failed(self) -> None:
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            patch.dict(os.environ, {"DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir}),
            self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            self._store_original_file(storage_dir)

            with patch(
                "documents.services.ocr_processor.OCRClient"
            ) as ocr_client_class:
                ocr_client_class.return_value.process_document.side_effect = (
                    RuntimeError("backend-ocr unavailable")
                )

                _run_document_processing(self.document.id, self.tenant, None)

        processing_run = OrchestrationRun.objects.get(name="document_processing")
        assert processing_run.status == OrchestrationRun.Status.FAILED

        tasks = list(processing_run.task_executions.all())
        assert len(tasks) == 1
        assert tasks[0].task_name == "ocr"
        assert tasks[0].status == "ERROR"
        assert tasks[0].attempt > 1

        self.document.refresh_from_db()
        assert self.document.status != Document.Status.VALIDATION_PENDING
