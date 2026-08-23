from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from docuparse_orchestrator.context import orchestration_run
from docuparse_storage import LocalStorage, document_original_key
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import Tenant, UserProfile
from users.models import Permission, Role

from documents.models import Document, ValidationDecision
from documents.services.processing_queue import _run_document_processing
from documents.views import validation_decision_task
from orchestrator.models import OrchestrationRun, TaskExecution


def _jwt_for(user, tenant) -> str:
    token = RefreshToken.for_user(user)
    token["tenant"] = tenant.slug
    return str(token.access_token)


class ProcessDashboardAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            slug="tenant-process-dashboard", name="Tenant Process Dashboard"
        )
        connection.set_tenant(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="operator", password="test"
        )
        role = Role.objects.create(name="Operador")
        role.permissions.set(
            [Permission.objects.create(code="operations.access", description="Ops")]
        )
        UserProfile.objects.create(user=self.user, tenant=self.tenant, role_ref=role)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {_jwt_for(self.user, self.tenant)}"
        )

        # Documento sem nenhuma execução — ex.: criado antes desta feature,
        # ou upload cujo auto-processamento nunca chegou a rodar.
        self.document_no_history = Document.objects.create(
            channel="manual",
            file_uri="local://placeholder",
            original_filename="no-history.pdf",
            content_type="application/pdf",
            size_bytes=10,
            status=Document.Status.RECEIVED,
        )

    def _create_document_with_file(self, storage_dir: str, filename: str) -> Document:
        document = Document.objects.create(
            channel="manual",
            file_uri="local://placeholder",
            original_filename=filename,
            content_type="application/pdf",
            size_bytes=10,
            status=Document.Status.RECEIVED,
        )
        stored = LocalStorage(storage_dir).put_bytes(
            document_original_key(self.tenant.slug, str(document.id)),
            b"%PDF fixture",
        )
        document.file_uri = stored.uri
        document.save(update_fields=["file_uri"])
        return document

    def test_dashboard_reflects_full_pipeline_and_can_retry(self) -> None:
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            patch.dict(os.environ, {"DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir}),
            self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            document_ok = self._create_document_with_file(storage_dir, "ok.pdf")
            document_error = self._create_document_with_file(storage_dir, "error.pdf")

            with (
                patch(
                    "documents.services.ocr_processor.OCRClient"
                ) as ocr_client_class,
                patch(
                    "documents.services.ocr_processor.LangExtractClient"
                ) as langextract_class,
            ):
                ocr_client_class.return_value.process_document.return_value = {
                    "raw_text": "algum texto",
                    "document_type": "digital_pdf",
                    "engine_used": "mock",
                }
                langextract_class.return_value.extract_with_schema.return_value = {
                    "fields": {},
                    "confidence": 0.5,
                    "requires_human_validation": True,
                }
                _run_document_processing(document_ok.id, self.tenant, None)

            with orchestration_run(
                "document_validation",
                document_id=str(document_ok.id),
                triggered_by=self.user.username,
            ):
                validation_decision_task(
                    document_ok.id,
                    ValidationDecision.Decision.APPROVED,
                    "",
                    {},
                    self.user.id,
                )

            with patch(
                "documents.services.ocr_processor.OCRClient"
            ) as ocr_client_class_error:
                ocr_client_class_error.return_value.process_document.side_effect = (
                    RuntimeError("backend-ocr indisponível")
                )
                _run_document_processing(document_error.id, self.tenant, None)

            # --- lista da sidebar ---
            list_response = self.client.get(reverse("processes-dashboard"))
            assert list_response.status_code == 200
            by_id = {row["id"]: row for row in list_response.json()["results"]}
            assert by_id[str(document_error.id)]["has_error"] is True
            assert by_id[str(document_ok.id)]["has_error"] is False
            assert by_id[str(self.document_no_history.id)]["has_error"] is False

            # --- detalhe: sem histórico ---
            no_history_response = self.client.get(
                reverse("document-pipeline", args=[self.document_no_history.id])
            )
            no_history_steps = {
                s["key"]: s for s in no_history_response.json()["steps"]
            }
            assert no_history_steps["register"]["status"] == "OK"
            assert no_history_steps["ocr"]["status"] == "PENDING"
            assert no_history_steps["ocr"]["executions"] == []
            assert no_history_steps["validation_decision"]["status"] == "PENDING"

            # --- detalhe: pipeline completo ---
            ok_response = self.client.get(
                reverse("document-pipeline", args=[document_ok.id])
            )
            ok_steps = {s["key"]: s for s in ok_response.json()["steps"]}
            assert ok_steps["ocr"]["status"] == "OK"
            assert ok_steps["ocr"]["retryable"] is True
            assert ok_steps["extraction"]["status"] == "OK"
            assert ok_steps["validation_decision"]["status"] == "OK"
            assert ok_steps["validation_decision"]["retryable"] is False

            # automatic pipeline run: no human triggered it
            assert ok_steps["ocr"]["executions"][0]["triggered_by"] is None
            assert ok_steps["extraction"]["executions"][0]["triggered_by"] is None
            # validation is always a human decision
            assert (
                ok_steps["validation_decision"]["executions"][0]["triggered_by"]
                == self.user.username
            )

            # --- detalhe: falha de OCR ---
            error_response = self.client.get(
                reverse("document-pipeline", args=[document_error.id])
            )
            error_steps = {s["key"]: s for s in error_response.json()["steps"]}
            assert error_steps["ocr"]["status"] == "ERROR"
            assert error_steps["ocr"]["executions"][0]["error_message"]
            assert error_steps["extraction"]["status"] == "PENDING"

            # --- retry manual do step com erro ---
            with patch(
                "documents.services.ocr_processor.OCRClient"
            ) as ocr_client_class_retry:
                ocr_client_class_retry.return_value.process_document.return_value = {
                    "raw_text": "recuperado",
                    "document_type": "digital_pdf",
                    "engine_used": "mock",
                }
                retry_response = self.client.post(
                    reverse("document-retry-step", args=[document_error.id, "ocr"])
                )

            assert retry_response.status_code == 200
            assert retry_response.json()["status"] == "ok"

            after_retry = self.client.get(
                reverse("document-pipeline", args=[document_error.id])
            )
            ocr_step_after_retry = next(
                s for s in after_retry.json()["steps"] if s["key"] == "ocr"
            )
            assert len(ocr_step_after_retry["executions"]) == 2
            assert ocr_step_after_retry["status"] == "OK"
            # newest execution first: the manual retry, attributed to the caller
            assert ocr_step_after_retry["executions"][0]["triggered_by"] == self.user.username
            assert ocr_step_after_retry["executions"][0]["run_name"] == "retry_ocr"
            # the original automatic attempt stays untouched
            assert ocr_step_after_retry["executions"][1]["triggered_by"] is None

            # --- retry recusado pra validation_decision ---
            rejected = self.client.post(
                reverse(
                    "document-retry-step", args=[document_ok.id, "validation_decision"]
                )
            )
            assert rejected.status_code == 400

        assert OrchestrationRun.objects.filter(
            document_id=document_ok.id, name="document_processing"
        ).exists()
        assert OrchestrationRun.objects.filter(
            document_id=document_ok.id, name="document_validation"
        ).exists()
        assert (
            TaskExecution.objects.filter(
                orchestration_run__document_id=document_error.id
            ).count()
            == 2
        )

    def test_retry_rejects_when_one_is_already_running_for_the_same_step(self) -> None:
        """Regression: a slow retry (LLM extraction can take 30-90s+) that
        the client gives up on and re-fires must not be allowed to stack a
        second concurrent execution for the same document/step."""
        from django.utils import timezone

        OrchestrationRun.objects.create(
            run_id="already-running-ocr",
            name="retry_ocr",
            status=OrchestrationRun.Status.RUNNING,
            started_at=timezone.now(),
            document_id=self.document_no_history.id,
        )

        response = self.client.post(
            reverse(
                "document-retry-step", args=[self.document_no_history.id, "ocr"]
            )
        )

        assert response.status_code == 409
        assert (
            TaskExecution.objects.filter(
                orchestration_run__document_id=self.document_no_history.id
            ).count()
            == 0
        )

    def test_processes_endpoints_require_operations_access(self) -> None:
        unprivileged = get_user_model().objects.create_user(
            username="no-access", password="test"
        )
        role = Role.objects.create(name="SemAcesso")
        UserProfile.objects.create(
            user=unprivileged, tenant=self.tenant, role_ref=role
        )
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {_jwt_for(unprivileged, self.tenant)}"
        )

        assert client.get(reverse("processes-dashboard")).status_code == 403
        assert (
            client.get(
                reverse("document-pipeline", args=[self.document_no_history.id])
            ).status_code
            == 403
        )
