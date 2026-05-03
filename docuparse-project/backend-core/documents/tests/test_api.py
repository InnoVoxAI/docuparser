from __future__ import annotations

import tempfile
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from docuparse_storage import LocalStorage, document_original_key
from docuparse_events import EventMessage, LocalJsonlEventBus, publish_dead_letter

from documents.models import Document, EmailSettings, ERPIntegrationAttempt, ExtractionResult, IntegrationSettings, LayoutConfig, OCRSettings, SchemaConfig, Tenant, ValidationDecision


class DocumentsAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="tenant-demo", name="Tenant Demo")
        self.user = get_user_model().objects.create_user(username="operator", password="test")
        self.document = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.VALIDATION_PENDING,
            channel="manual",
            file_uri="local://documents/tenant-demo/doc/original",
            original_filename="fixture.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

    def test_inbox_and_detail_endpoints(self) -> None:
        inbox = self.client.get(reverse("documents-inbox"), {"status": Document.Status.VALIDATION_PENDING})
        detail = self.client.get(reverse("document-detail", args=[self.document.id]))

        assert inbox.status_code == 200
        assert inbox.json()[0]["id"] == str(self.document.id)
        assert detail.status_code == 200
        assert detail.json()["file_uri"] == self.document.file_uri

    def test_document_received_event_endpoint_registers_document(self) -> None:
        from datetime import datetime, timezone
        from uuid import uuid4

        document_id = uuid4()
        with self.settings(DOCUPARSE_AUTO_PROCESS_OCR=False):
            response = self.client.post(
                reverse("document-received-event"),
                {
                    "event_id": str(uuid4()),
                    "event_type": "document.received",
                    "event_version": "v1",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "tenant_id": self.tenant.slug,
                    "document_id": str(document_id),
                    "correlation_id": str(uuid4()),
                    "source": "backend-com",
                    "data": {
                        "channel": "manual",
                        "received_at": datetime.now(timezone.utc).isoformat(),
                        "sender": "operator@example.test",
                        "file": {
                            "uri": "local://documents/tenant-demo/new/original",
                            "content_type": "application/pdf",
                            "filename": "new.pdf",
                            "size_bytes": 123,
                        },
                        "metadata": {},
                    },
                },
                format="json",
            )

        assert response.status_code == 201
        assert Document.objects.get(id=document_id).original_filename == "new.pdf"

    def test_document_received_event_starts_automatic_ocr_when_enabled(self) -> None:
        from datetime import datetime, timezone
        from uuid import uuid4

        document_id = uuid4()
        with patch("documents.views.start_document_ocr_thread") as start_thread:
            response = self.client.post(
                reverse("document-received-event"),
                {
                    "event_id": str(uuid4()),
                    "event_type": "document.received",
                    "event_version": "v1",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "tenant_id": self.tenant.slug,
                    "document_id": str(document_id),
                    "correlation_id": str(uuid4()),
                    "source": "backend-com",
                    "data": {
                        "channel": "manual",
                        "received_at": datetime.now(timezone.utc).isoformat(),
                        "sender": "operator@example.test",
                        "file": {
                            "uri": "local://documents/tenant-demo/new-auto/original",
                            "content_type": "application/pdf",
                            "filename": "new-auto.pdf",
                            "size_bytes": 123,
                        },
                        "metadata": {},
                    },
                },
                format="json",
            )

        assert response.status_code == 201
        start_thread.assert_called_once_with(document_id)

    def test_document_file_endpoint_serves_original_file(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            stored = LocalStorage(storage_dir).put_bytes(
                document_original_key(self.tenant.slug, str(self.document.id)),
                b"%PDF original",
            )
            self.document.file_uri = stored.uri
            self.document.save(update_fields=["file_uri"])

            response = self.client.get(reverse("document-file", args=[self.document.id]))

        assert response.status_code == 200
        assert b"".join(response.streaming_content) == b"%PDF original"

    def test_process_ocr_endpoint_updates_extraction_result(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            stored = LocalStorage(storage_dir).put_bytes(
                document_original_key(self.tenant.slug, str(self.document.id)),
                b"%PDF original",
            )
            self.document.file_uri = stored.uri
            self.document.save(update_fields=["file_uri"])
            with patch("documents.services.ocr_processor.OCRClient") as client_class:
                client_class.return_value.process_document.return_value = {
                    "fields": {"valor": "R$ 123,45"},
                    "final_score": 0.82,
                    "raw_text": "valor R$ 123,45",
                    "document_type": "scanned_image",
                    "engine_used": "mock",
                }

                response = self.client.post(reverse("document-process-ocr", args=[self.document.id]))

        self.document.refresh_from_db()
        extraction = self.document.extraction_result
        assert response.status_code == 200
        assert self.document.status == Document.Status.VALIDATION_PENDING
        assert extraction.fields == {"valor": "R$ 123,45"}
        assert extraction.confidence == 0.82
        assert response.json()["full_transcription"] == "valor R$ 123,45"
        assert response.json()["ocr_metadata"] == {
            "engine_used": "mock",
            "classification": "scanned_image",
            "preprocessing_hint": "",
            "classification_engine_preprocessing_hints": {},
        }

    def test_reprocess_ocr_endpoint_replaces_existing_extraction_result(self) -> None:
        ExtractionResult.objects.create(
            document=self.document,
            schema_id="legacy_ocr",
            schema_version="v1",
            fields={"valor": "antigo"},
            confidence=0.1,
            requires_human_validation=True,
        )
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            stored = LocalStorage(storage_dir).put_bytes(
                document_original_key(self.tenant.slug, str(self.document.id)),
                b"%PDF original",
            )
            self.document.file_uri = stored.uri
            self.document.save(update_fields=["file_uri"])
            with patch("documents.services.ocr_processor.OCRClient") as client_class:
                client_class.return_value.process_document.return_value = {
                    "fields": {"valor": "novo"},
                    "final_score": 0.77,
                    "raw_text": "valor novo",
                    "document_type": "digital_pdf",
                    "engine_used": "docling",
                }

                response = self.client.post(reverse("document-reprocess-ocr", args=[self.document.id]))

        self.document.refresh_from_db()
        assert response.status_code == 200
        assert self.document.extraction_result.fields == {"valor": "novo"}
        assert self.document.extraction_result.confidence == 0.77
        assert response.json()["full_transcription"] == "valor novo"

    def test_delete_document_endpoint_removes_database_row_and_preserves_storage(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            storage = LocalStorage(storage_dir)
            stored = storage.put_bytes(
                document_original_key(self.tenant.slug, str(self.document.id)),
                b"%PDF original",
            )
            self.document.file_uri = stored.uri
            self.document.save(update_fields=["file_uri"])

            response = self.client.delete(reverse("document-delete", args=[self.document.id]))

            assert response.status_code == 204
            assert not Document.objects.filter(id=self.document.id).exists()
            assert storage.get_bytes(stored.uri) == b"%PDF original"

    def test_operational_api_requires_internal_token_when_configured(self) -> None:
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN="secret"):
            rejected = self.client.get(reverse("documents-inbox"))
            accepted = self.client.get(reverse("documents-inbox"), HTTP_AUTHORIZATION="Bearer secret")

        assert rejected.status_code == 401
        assert accepted.status_code == 200

    def test_operator_can_approve_document_via_api(self) -> None:
        response = self.client.post(
            reverse("document-validate", args=[self.document.id]),
            {
                "decision": ValidationDecision.Decision.APPROVED,
                "decided_by_id": self.user.id,
            },
            format="json",
        )

        assert response.status_code == 201
        self.document.refresh_from_db()
        assert self.document.status == Document.Status.ERP_INTEGRATION_REQUESTED
        assert self.document.validation_decisions.count() == 1

    def test_approve_document_publishes_erp_integration_requested_and_exports_json(self) -> None:
        with tempfile.TemporaryDirectory() as event_dir, tempfile.TemporaryDirectory() as export_dir, self.settings(
            DOCUPARSE_LOCAL_EVENT_DIR=event_dir,
            DOCUPARSE_APPROVED_EXPORT_DIR=export_dir,
        ):
            ExtractionResult.objects.create(
                document=self.document,
                schema_id="boleto",
                schema_version="v1",
                fields={"valor": "R$ 123,45"},
                confidence=0.9,
                requires_human_validation=False,
            )
            response = self.client.post(
                reverse("document-validate", args=[self.document.id]),
                {
                    "decision": ValidationDecision.Decision.APPROVED,
                    "decided_by_id": self.user.id,
                },
                format="json",
            )

            events = LocalJsonlEventBus(event_dir).consume("erp.integration.requested")
            export_path = events[0]["data"]["metadata"]["approved_export_path"]
            exported = json.loads(open(export_path, encoding="utf-8").read())

        assert response.status_code == 201
        assert ERPIntegrationAttempt.objects.count() == 1
        assert len(events) == 1
        assert events[0]["event_type"] == "erp.integration.requested"
        assert events[0]["data"]["payload"]["fields"] == {"valor": "R$ 123,45"}
        assert exported["document_id"] == str(self.document.id)
        assert exported["payload"]["fields"] == {"valor": "R$ 123,45"}

    def test_approve_document_uses_corrected_fields_for_export(self) -> None:
        with tempfile.TemporaryDirectory() as event_dir, tempfile.TemporaryDirectory() as export_dir, self.settings(
            DOCUPARSE_LOCAL_EVENT_DIR=event_dir,
            DOCUPARSE_APPROVED_EXPORT_DIR=export_dir,
        ):
            extraction = ExtractionResult.objects.create(
                document=self.document,
                schema_id="boleto",
                schema_version="v1",
                fields={"valor": "R$ 123,45"},
                confidence=0.9,
                requires_human_validation=True,
            )
            response = self.client.post(
                reverse("document-validate", args=[self.document.id]),
                {
                    "decision": ValidationDecision.Decision.APPROVED,
                    "decided_by_id": self.user.id,
                    "corrected_fields": {"valor": "R$ 999,99"},
                },
                format="json",
            )

            events = LocalJsonlEventBus(event_dir).consume("erp.integration.requested")

        extraction.refresh_from_db()
        assert response.status_code == 201
        assert extraction.fields == {"valor": "R$ 999,99"}
        assert events[0]["data"]["payload"]["fields"] == {"valor": "R$ 999,99"}

    def test_integration_settings_endpoint_persists_non_secret_fields(self) -> None:
        response = self.client.get(reverse("integration-settings"), {"tenant": self.tenant.slug})
        update = self.client.patch(
            reverse("integration-settings"),
            {
                "tenant_slug": self.tenant.slug,
                "approved_export_enabled": False,
                "approved_export_dir": "/tmp/docuparse-approved",
                "approved_export_format": "json",
                "superlogica_base_url": "https://sandbox.superlogica.example",
                "superlogica_mode": "mock",
            },
            format="json",
        )

        config = IntegrationSettings.objects.get(tenant=self.tenant)
        assert response.status_code == 200
        assert response.json()["approved_export_enabled"] is True
        assert update.status_code == 200
        assert update.json()["superlogica_mode"] == "mock"
        assert config.approved_export_enabled is False
        assert config.superlogica_base_url == "https://sandbox.superlogica.example"

    def test_approval_respects_disabled_json_export_setting(self) -> None:
        IntegrationSettings.objects.create(
            tenant=self.tenant,
            approved_export_enabled=False,
            approved_export_dir="/tmp/ignored",
            approved_export_format=IntegrationSettings.ExportFormat.JSON,
        )
        with tempfile.TemporaryDirectory() as event_dir, tempfile.TemporaryDirectory() as export_dir, self.settings(
            DOCUPARSE_LOCAL_EVENT_DIR=event_dir,
            DOCUPARSE_APPROVED_EXPORT_DIR=export_dir,
        ):
            ExtractionResult.objects.create(
                document=self.document,
                schema_id="boleto",
                schema_version="v1",
                fields={"valor": "R$ 123,45"},
                confidence=0.9,
                requires_human_validation=False,
            )
            response = self.client.post(
                reverse("document-validate", args=[self.document.id]),
                {
                    "decision": ValidationDecision.Decision.APPROVED,
                    "decided_by_id": self.user.id,
                },
                format="json",
            )

            events = LocalJsonlEventBus(event_dir).consume("erp.integration.requested")

        assert response.status_code == 201
        assert events[0]["data"]["metadata"]["approved_export_enabled"] is False
        assert events[0]["data"]["metadata"]["approved_export_path"] == ""

    def test_ocr_settings_endpoint_persists_non_secret_fields(self) -> None:
        response = self.client.get(reverse("ocr-settings"), {"tenant": self.tenant.slug})
        update = self.client.patch(
            reverse("ocr-settings"),
            {
                "tenant_slug": self.tenant.slug,
                "digital_pdf_engine": "docling",
                "scanned_image_engine": "openrouter",
                "handwritten_engine": "openrouter",
                "technical_fallback_engine": "tesseract",
                "openrouter_model": "google/gemini-2.5-flash-preview",
                "openrouter_fallback_model": "qwen/qwen2.5-vl-72b-instruct",
                "timeout_seconds": 180,
                "retry_empty_text_enabled": True,
                "digital_pdf_min_text_blocks": 10,
            },
            format="json",
        )

        config = OCRSettings.objects.get(tenant=self.tenant)
        assert response.status_code == 200
        assert response.json()["digital_pdf_engine"] == "docling"
        assert update.status_code == 200
        assert update.json()["timeout_seconds"] == 180
        assert config.openrouter_model == "google/gemini-2.5-flash-preview"
        assert config.digital_pdf_min_text_blocks == 10

    def test_email_settings_endpoint_persists_non_secret_fields(self) -> None:
        response = self.client.get(reverse("email-settings"), {"tenant": self.tenant.slug})
        update = self.client.patch(
            reverse("email-settings"),
            {
                "tenant_slug": self.tenant.slug,
                "provider": "imap",
                "inbox_folder": "INBOX/Docs",
                "imap_host": "imap.example.test",
                "imap_port": 993,
                "username": "docs@example.test",
                "webhook_url": "http://127.0.0.1:8070/api/v1/email/messages",
                "accepted_content_types": "application/pdf,image/jpeg",
                "max_attachment_mb": 15,
                "blocked_senders": "blocked@example.test",
                "is_active": True,
            },
            format="json",
        )

        config = EmailSettings.objects.get(tenant=self.tenant)
        assert response.status_code == 200
        assert response.json()["provider"] == "imap"
        assert update.status_code == 200
        assert update.json()["imap_host"] == "imap.example.test"
        assert config.inbox_folder == "INBOX/Docs"
        assert config.blocked_senders == "blocked@example.test"

    def test_schema_and_layout_config_endpoints(self) -> None:
        schema_response = self.client.post(
            reverse("schema-configs"),
            {
                "tenant_slug": self.tenant.slug,
                "schema_id": "boleto",
                "version": "v1",
                "definition": {"fields": ["valor"]},
                "is_active": True,
            },
            format="json",
        )
        assert schema_response.status_code == 201
        schema = SchemaConfig.objects.get()

        layout_response = self.client.post(
            reverse("layout-configs"),
            {
                "tenant_slug": self.tenant.slug,
                "layout": "boleto_bb",
                "document_type": "scanned_image",
                "schema_config_id": str(schema.id),
                "confidence_threshold": 0.8,
            },
            format="json",
        )

        assert layout_response.status_code == 201
        assert LayoutConfig.objects.get().schema_config == schema
        assert self.client.get(reverse("schema-configs")).status_code == 200
        assert self.client.get(reverse("layout-configs")).status_code == 200

        draft_response = self.client.patch(
            reverse("schema-config-detail", args=[schema.id]),
            {
                "definition": {"fields": ["valor", "vencimento"], "status": "draft"},
                "is_active": True,
            },
            format="json",
        )

        schema.refresh_from_db()
        assert draft_response.status_code == 200
        assert schema.definition == {"fields": ["valor", "vencimento"], "status": "draft"}

    def test_dlq_operation_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as event_dir, self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir):
            bus = LocalJsonlEventBus(event_dir)
            publish_dead_letter(
                bus,
                stream="ocr.completed",
                entry=EventMessage(id=1, payload={"event_type": "ocr.completed", "event_id": "event-1"}),
                error=ValueError("invalid event"),
                source="layout-service",
            )

            summary = self.client.get(reverse("dlq-summary"))
            events = self.client.get(reverse("dlq-events"), {"stream": "ocr.completed.dlq"})
            dry_run = self.client.post(
                reverse("dlq-requeue"),
                {"stream": "ocr.completed.dlq", "id": "1", "execute": False},
                format="json",
            )
            requeue = self.client.post(
                reverse("dlq-requeue"),
                {"stream": "ocr.completed.dlq", "id": "1", "execute": True, "note": "reviewed"},
                format="json",
            )
            invalid = self.client.get(reverse("dlq-events"), {"stream": "not.allowed.dlq"})
            invalid_requeue = self.client.post(
                reverse("dlq-requeue"),
                {"stream": "not.allowed.dlq", "id": "1", "execute": True},
                format="json",
            )
            requeued_events = bus.consume("ocr.completed")

        assert summary.status_code == 200
        assert summary.json()["total"] == 1
        assert events.status_code == 200
        assert events.json()["stream"] == "ocr.completed.dlq"
        assert events.json()["entries"][0]["error_type"] == "ValueError"
        assert dry_run.status_code == 200
        assert dry_run.json()["execute"] is False
        assert requeue.status_code == 202
        assert requeue.json()["target_stream"] == "ocr.completed"
        assert requeued_events[0]["event_id"] == "event-1"
        assert invalid.status_code == 400
        assert invalid_requeue.status_code == 400
