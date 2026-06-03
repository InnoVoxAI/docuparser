from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import Document, ExtractionResult, Tenant, ValidationDecision


class ValidationViewGuardTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="tenant-test", name="Tenant Test")
        self.user = get_user_model().objects.create_user(username="op", password="test")
        self.document = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.EXTRACTION_COMPLETED,
            channel="manual",
            file_uri="local://documents/tenant-test/doc/original",
            original_filename="test.pdf",
            content_type="application/pdf",
            size_bytes=512,
        )
        self.extraction = ExtractionResult.objects.create(
            document=self.document,
            schema_id="test_schema",
            schema_version="v1",
            fields={"campo": "valor"},
            confidence=0.9,
        )
        self.payload_base = {"decided_by_id": str(self.user.id)}

    def _url(self):
        return reverse("document-validate", args=[self.document.id])

    def test_approve_with_extraction_returns_201_and_approved_status(self) -> None:
        from unittest.mock import patch
        with patch("documents.views.publish_erp_integration_requested"):
            response = self.client.post(self._url(), {**self.payload_base, "decision": "approved"}, format="json")
        self.document.refresh_from_db()

        assert response.status_code == 201
        assert self.document.status == Document.Status.APPROVED
        assert ValidationDecision.objects.filter(document=self.document, decision="approved").exists()

    def test_approve_without_extraction_returns_422(self) -> None:
        self.extraction.delete()
        response = self.client.post(self._url(), {**self.payload_base, "decision": "approved"}, format="json")

        assert response.status_code == 422
        assert "Extração" in response.json()["detail"]

    def test_reject_with_valid_notes_returns_201_and_persists_notes(self) -> None:
        response = self.client.post(
            self._url(),
            {**self.payload_base, "decision": "rejected", "notes": "Documento ilegível"},
            format="json",
        )
        self.document.refresh_from_db()

        assert response.status_code == 201
        assert self.document.status == Document.Status.REJECTED
        decision = ValidationDecision.objects.get(document=self.document, decision="rejected")
        assert decision.notes == "Documento ilegível"

    def test_reject_with_empty_notes_returns_400(self) -> None:
        response = self.client.post(
            self._url(),
            {**self.payload_base, "decision": "rejected", "notes": ""},
            format="json",
        )

        assert response.status_code == 400
        assert "obrigatório" in response.json()["detail"]

    def test_reject_with_whitespace_only_notes_returns_400(self) -> None:
        response = self.client.post(
            self._url(),
            {**self.payload_base, "decision": "rejected", "notes": "   "},
            format="json",
        )

        assert response.status_code == 400
        assert "obrigatório" in response.json()["detail"]
