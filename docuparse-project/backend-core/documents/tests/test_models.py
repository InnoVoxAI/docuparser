from __future__ import annotations

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from documents.models import (
    Document,
    DocumentEvent,
    ERPIntegrationAttempt,
    ExtractionResult,
    LayoutConfig,
    SchemaConfig,
    Tenant,
    UserProfile,
    ValidationDecision,
)


class CoreDomainModelTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-demo", name="Tenant Demo")
        self.user = get_user_model().objects.create_user(username="operator", password="test")
        self.profile = UserProfile.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=UserProfile.Role.OPERATOR,
        )
        self.document = Document.objects.create(
            tenant=self.tenant,
            channel="manual",
            file_uri="local://documents/tenant-demo/doc/original",
            original_filename="fixture.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

    def test_document_state_transition_is_persisted(self) -> None:
        self.document.transition_to(Document.Status.OCR_COMPLETED)

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.OCR_COMPLETED

    def test_document_event_is_idempotent_by_event_id(self) -> None:
        event_id = uuid4()
        payload = {"event_type": "document.received"}
        DocumentEvent.objects.create(
            event_id=event_id,
            tenant=self.tenant,
            document=self.document,
            event_type="document.received",
            correlation_id=self.document.correlation_id,
            source="backend-com",
            occurred_at=timezone.now(),
            payload=payload,
        )

        with self.assertRaises(IntegrityError):
            DocumentEvent.objects.create(
                event_id=event_id,
                tenant=self.tenant,
                document=self.document,
                event_type="document.received",
                correlation_id=self.document.correlation_id,
                source="backend-com",
                occurred_at=timezone.now(),
                payload=payload,
            )

    def test_extraction_validation_and_erp_attempts_are_related_to_document(self) -> None:
        extraction = ExtractionResult.objects.create(
            document=self.document,
            schema_id="boleto",
            schema_version="v1",
            fields={"valor": "R$ 123,45"},
            confidence=0.9,
            requires_human_validation=False,
        )
        decision = ValidationDecision.objects.create(
            document=self.document,
            decided_by=self.user,
            decision=ValidationDecision.Decision.APPROVED,
            corrected_fields={},
        )
        attempt = ERPIntegrationAttempt.objects.create(
            document=self.document,
            connector="mock",
            idempotency_key=f"{self.tenant.slug}:{self.document.id}:v1",
            request_payload={"valor": "R$ 123,45"},
        )

        assert self.document.extraction_result == extraction
        assert self.document.validation_decisions.get() == decision
        assert self.document.erp_attempts.get() == attempt

    def test_schema_and_layout_config_are_unique_per_tenant(self) -> None:
        schema = SchemaConfig.objects.create(
            tenant=self.tenant,
            schema_id="boleto",
            version="v1",
            definition={"fields": ["valor"]},
        )
        LayoutConfig.objects.create(
            tenant=self.tenant,
            layout="boleto_bb",
            document_type="scanned_image",
            schema_config=schema,
        )

        with self.assertRaises(IntegrityError):
            LayoutConfig.objects.create(
                tenant=self.tenant,
                layout="boleto_bb",
                document_type="scanned_image",
                schema_config=schema,
            )
