from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from documents.models import Document, ExtractionResult, ValidationDecision
from tenants.models import Tenant, UserProfile
from users.models import Permission, Role


def _jwt_for(user, tenant) -> str:
    token = RefreshToken.for_user(user)
    token["tenant"] = tenant.slug
    return str(token.access_token)


class DocumentsInboxViewApprovedFilterTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="tenant-inbox", name="Tenant Inbox")
        connection.set_tenant(self.tenant)
        self.user = get_user_model().objects.create_user(username="inbox_op", password="test")
        # feature 009: o endpoint exige JWT do usuário com permissão "inbox.view".
        permission = Permission.objects.create(code="inbox.view", description="Inbox view")
        role = Role.objects.create(name="Operador")
        role.permissions.add(permission)
        UserProfile.objects.create(user=self.user, tenant=self.tenant, role_ref=role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {_jwt_for(self.user, self.tenant)}")

        self.approved_doc = Document.objects.create(
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
        assert data["count"] == 1
        assert data["results"][0]["id"] == str(self.approved_doc.id)
        assert data["results"][0]["status"] == "APPROVED"

    def test_approved_documents_have_non_null_decision_date(self) -> None:
        response = self.client.get(reverse("documents-inbox"), {"status": "APPROVED"})

        assert response.status_code == 200
        doc_data = response.json()["results"][0]
        assert doc_data["decision_date"] is not None
        assert doc_data["decision_date"] == self.decision.created_at.isoformat()
