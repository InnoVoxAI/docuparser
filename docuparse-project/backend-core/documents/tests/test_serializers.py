from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from documents.models import Document, ExtractionResult, Tenant, ValidationDecision
from documents.serializers import DocumentListSerializer


class DocumentListSerializerDecisionDateTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-serial", name="Tenant Serial")
        self.user = get_user_model().objects.create_user(username="serial_op", password="test")
        self.document = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.VALIDATION_PENDING,
            channel="manual",
            file_uri="local://documents/tenant-serial/doc/original",
            original_filename="serial.pdf",
            content_type="application/pdf",
            size_bytes=256,
        )

    def test_decision_date_is_null_when_no_validation_decision_exists(self) -> None:
        serializer = DocumentListSerializer(self.document)
        assert serializer.data["decision_date"] is None

    def test_decision_date_returns_created_at_of_most_recent_decision(self) -> None:
        ExtractionResult.objects.create(
            document=self.document,
            schema_id="s",
            schema_version="v1",
            fields={},
            confidence=1.0,
        )
        decision = ValidationDecision.objects.create(
            document=self.document,
            decided_by=self.user,
            decision="approved",
            notes="",
        )
        serializer = DocumentListSerializer(self.document)
        assert serializer.data["decision_date"] == decision.created_at.isoformat()
