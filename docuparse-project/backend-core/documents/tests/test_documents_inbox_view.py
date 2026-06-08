from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import Document, ExtractionResult, Tenant, ValidationDecision


class DocumentsInboxViewApprovedFilterTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="tenant-inbox", name="Tenant Inbox")
        self.user = get_user_model().objects.create_user(username="inbox_op", password="test")

        self.approved_doc = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.APPROVED,
            channel="manual",
            file_uri="local://documents/tenant-inbox/approved/original",
            original_filename="approved.pdf",
            content_type="application/pdf",
            size_bytes=512,
        )
        ExtractionResult.objects.create(
            document=self.approved_doc,
            schema_id="s",
            schema_version="v1",
            fields={},
            confidence=1.0,
        )
        self.decision = ValidationDecision.objects.create(
            document=self.approved_doc,
            decided_by=self.user,
            decision="approved",
            notes="",
        )
        Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.VALIDATION_PENDING,
            channel="manual",
            file_uri="local://documents/tenant-inbox/pending/original",
            original_filename="pending.pdf",
            content_type="application/pdf",
            size_bytes=512,
        )

    def test_status_approved_filter_returns_only_approved_documents(self) -> None:
        response = self.client.get(reverse("documents-inbox"), {"status": "APPROVED"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(self.approved_doc.id)
        assert data[0]["status"] == "APPROVED"

    def test_approved_documents_have_non_null_decision_date(self) -> None:
        response = self.client.get(reverse("documents-inbox"), {"status": "APPROVED"})

        assert response.status_code == 200
        doc_data = response.json()[0]
        assert doc_data["decision_date"] is not None
        assert doc_data["decision_date"] == self.decision.created_at.isoformat()
