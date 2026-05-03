from __future__ import annotations

import base64
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

PROJECT_DIR = Path(__file__).resolve().parents[3]
BACKEND_COM_SRC = PROJECT_DIR / "backend-com" / "src"
if str(BACKEND_COM_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_COM_SRC))

from backend_com import config as backend_com_config
from backend_com.services import document_ingest
from backend_com.services.email_capture import process_email_attachments
from backend_com.services.manual_upload import process_manual_upload
from backend_com.services.whatsapp_capture import process_whatsapp_media
from docuparse_events import LocalJsonlEventBus
from events import ExtractionCompletedEvent

from documents.models import Document, ERPIntegrationAttempt, Tenant, ValidationDecision
from documents.services.erp_mock import handle_erp_integration_requested_event
from documents.services.event_consumers import (
    consume_document_received,
    consume_erp_sent,
    consume_extraction_completed,
)


class LocalChannelToERPMockE2ETests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="tenant-demo", name="Tenant Demo")
        self.user = get_user_model().objects.create_user(username="operator", password="test")

    def test_manual_upload_reaches_erp_sent_with_exported_json(self) -> None:
        capture = lambda: process_manual_upload(
            tenant_id=self.tenant.slug,
            filename="manual.pdf",
            content_type="application/pdf",
            content=b"%PDF manual",
            sender="operator@example.test",
        )

        self._assert_channel_reaches_erp_sent(capture, "manual")

    def test_email_attachment_reaches_erp_sent_with_exported_json(self) -> None:
        capture = lambda: process_email_attachments(
            tenant_id=self.tenant.slug,
            sender="sender@example.test",
            message_id="msg-1",
            subject="Documentos",
            provider="webhook",
            attachments=[
                {
                    "filename": "email.pdf",
                    "content_type": "application/pdf",
                    "content": b"%PDF email",
                }
            ],
        )[0]

        self._assert_channel_reaches_erp_sent(capture, "email")

    def test_whatsapp_media_reaches_erp_sent_with_exported_json(self) -> None:
        capture = lambda: process_whatsapp_media(
            tenant_id=self.tenant.slug,
            sender="whatsapp:+5511999999999",
            message_sid="SM123",
            body="segue documento",
            media_items=[
                {
                    "filename": "whatsapp.pdf",
                    "content_type": "application/pdf",
                    "content_base64": base64.b64encode(b"%PDF whatsapp").decode("ascii"),
                }
            ],
        )[0]

        self._assert_channel_reaches_erp_sent(capture, "whatsapp")

    def _assert_channel_reaches_erp_sent(self, capture, expected_channel: str) -> None:
        with tempfile.TemporaryDirectory() as event_dir, tempfile.TemporaryDirectory() as storage_dir, tempfile.TemporaryDirectory() as export_dir, self.settings(
            DOCUPARSE_LOCAL_EVENT_DIR=event_dir,
            DOCUPARSE_APPROVED_EXPORT_DIR=export_dir,
        ):
            self._point_backend_com_to_tmp(storage_dir, event_dir)
            bus = LocalJsonlEventBus(event_dir)

            capture()
            received = bus.consume("document.received")
            assert len(received) == 1
            consume_document_received(received[0])

            document = Document.objects.get(id=received[0]["document_id"])
            assert document.channel == expected_channel

            extraction_event = ExtractionCompletedEvent(
                tenant_id=self.tenant.slug,
                document_id=document.id,
                correlation_id=document.correlation_id,
                occurred_at=datetime.now(timezone.utc),
                source="e2e-test",
                data={
                    "schema_id": "boleto",
                    "schema_version": "v1",
                    "fields": {"valor": "R$ 123,45", "canal": expected_channel},
                    "confidence": 0.92,
                    "requires_human_validation": True,
                    "metadata": {"mock": True},
                },
            ).model_dump(mode="json")
            bus.publish("extraction.completed", extraction_event)
            consume_extraction_completed(extraction_event)

            approval = self.client.post(
                reverse("document-validate", args=[document.id]),
                {
                    "decision": ValidationDecision.Decision.APPROVED,
                    "decided_by_id": self.user.id,
                },
                format="json",
            )
            assert approval.status_code == 201

            erp_requested = bus.consume("erp.integration.requested")
            assert len(erp_requested) == 1
            sent_event = handle_erp_integration_requested_event(erp_requested[0], bus)
            consume_erp_sent(sent_event)

            document.refresh_from_db()
            attempt = ERPIntegrationAttempt.objects.get(document=document)
            export_path = Path(erp_requested[0]["data"]["metadata"]["approved_export_path"])
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            sent_events = bus.consume("erp.sent")

        assert document.status == Document.Status.ERP_SENT
        assert attempt.status == ERPIntegrationAttempt.Status.SENT
        assert exported["payload"]["fields"]["canal"] == expected_channel
        assert sent_events[0]["event_type"] == "erp.sent"

    @staticmethod
    def _point_backend_com_to_tmp(storage_dir: str, event_dir: str) -> None:
        storage_path = Path(storage_dir)
        event_path = Path(event_dir)
        backend_com_config.settings.local_storage_dir = storage_path
        backend_com_config.settings.local_event_dir = event_path
        backend_com_config.settings.email_webhook_token = ""
        backend_com_config.settings.whatsapp_webhook_token = ""
        backend_com_config.settings.internal_service_token = ""
        document_ingest.settings.local_storage_dir = storage_path
        document_ingest.settings.local_event_dir = event_path
        document_ingest.settings.email_webhook_token = ""
        document_ingest.settings.whatsapp_webhook_token = ""
