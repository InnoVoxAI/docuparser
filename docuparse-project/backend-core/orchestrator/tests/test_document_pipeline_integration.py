from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import requests
from catalog.models import LayoutConfig, SchemaConfig
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from documents.models import Document, ValidationDecision
from documents.services.processing_queue import _run_document_processing
from documents.views import validation_decision_task
from docuparse_orchestrator.context import orchestration_run
from docuparse_storage import LocalStorage, document_original_key
from tenants.models import Tenant

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

    def _run_with_ocr_http(self, side_effect) -> MagicMock:
        """Roda o pipeline com o OCRClient real e o HTTP simulado em
        `requests.request` (service_errors.request_json). Devolve o mock para
        contar quantas chamadas ao OCR (pago) foram feitas."""
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            patch.dict(os.environ, {"DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir}),
            self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            self._store_original_file(storage_dir)
            with patch(
                "documents.services.service_errors.requests.request",
                side_effect=side_effect,
            ) as http_request:
                _run_document_processing(self.document.id, self.tenant, None)
        return http_request

    def _assert_ocr_failed(self, *, attempt: int, error_type: str) -> None:
        processing_run = OrchestrationRun.objects.get(name="document_processing")
        assert processing_run.status == OrchestrationRun.Status.FAILED

        tasks = list(processing_run.task_executions.all())
        assert len(tasks) == 1
        assert tasks[0].task_name == "ocr"
        assert tasks[0].status == "ERROR"
        assert tasks[0].attempt == attempt
        assert tasks[0].error_type == error_type

        self.document.refresh_from_db()
        assert self.document.status != Document.Status.VALIDATION_PENDING

    def test_ocr_http_400_is_permanent_and_calls_ocr_once(self) -> None:
        """AR-27 (aceite): um 400 do OCR não faz retry — 1 chamada paga."""
        http_request = self._run_with_ocr_http(
            [_http_response(400, "arquivo inválido")]
        )

        assert http_request.call_count == 1
        self._assert_ocr_failed(attempt=1, error_type="PermanentServiceError")

    def test_ocr_timeout_is_transient_and_calls_ocr_three_times(self) -> None:
        """AR-27 (aceite): timeout de conexão faz retry até max_attempts (3)."""
        http_request = self._run_with_ocr_http(
            requests.ConnectTimeout("connect timeout")
        )

        assert http_request.call_count == 3
        self._assert_ocr_failed(attempt=3, error_type="TransientServiceError")

    def test_ocr_http_500_and_read_timeout_are_permanent(self) -> None:
        """O backend-ocr devolve 500 para qualquer erro do OpenRouter (até
        400/401), e um ReadTimeout quer dizer que o OCR provavelmente rodou —
        nenhum dos dois pode cobrar de novo."""
        http_request = self._run_with_ocr_http([_http_response(500, "Erro interno")])
        assert http_request.call_count == 1
        self._assert_ocr_failed(attempt=1, error_type="PermanentServiceError")

        OrchestrationRun.objects.all().delete()
        http_request = self._run_with_ocr_http(requests.ReadTimeout("read timeout"))
        assert http_request.call_count == 1
        self._assert_ocr_failed(attempt=1, error_type="PermanentServiceError")

    def test_ocr_transient_then_success_continues_pipeline(self) -> None:
        """503 seguido de sucesso: a task fica OK com attempt=2."""
        http_request = self._run_with_ocr_http(
            [
                _http_response(503, "indisponível"),
                _http_response(
                    200,
                    json_body={"raw_text": "texto", "document_type": "boleto"},
                ),
                # langextract-service
                _http_response(200, json_body={"fields": {"valor": "10"}}),
            ]
        )

        assert http_request.call_count == 3
        processing_run = OrchestrationRun.objects.get(name="document_processing")
        ocr_execution = processing_run.task_executions.get(task_name="ocr")
        assert ocr_execution.status == "OK"
        assert ocr_execution.attempt == 2

    def test_non_http_ocr_failure_is_not_retried(self) -> None:
        """Erro que não é TransientServiceError (aqui um RuntimeError genérico)
        encerra na primeira tentativa e marca o run como FAILED."""
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

        assert ocr_client_class.return_value.process_document.call_count == 1
        self._assert_ocr_failed(attempt=1, error_type="RuntimeError")


def _http_response(
    status_code: int, text: str = "", *, json_body: dict | None = None
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    if json_body is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = json_body
    return response
