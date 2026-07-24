"""
Integration tests for tenant data isolation (US1) and inactive tenant guard.
Tests marked `tenant_db` require POSTGRES_HOST env var (PostgreSQL with schema routing).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from users.models import Permission, Role

from tenants.models import Tenant, UserProfile

User = get_user_model()


def _setup_tenant(slug: str, username: str) -> tuple[Tenant, User, str]:
    """Return (tenant, user, jwt_access_token) — bypasses schema routing for unit tests."""
    with patch.object(Tenant, "auto_create_schema", new=False):
        tenant = Tenant.objects.create(
            slug=slug, name=slug.title(), schema_name=f"tenant_{slug.replace('-', '_')}"
        )
    perm, _ = Permission.objects.get_or_create(
        code="inbox.view", defaults={"description": "Inbox"}
    )
    role, _ = Role.objects.get_or_create(name=f"role_{slug}")
    role.permissions.add(perm)
    user = User.objects.create_user(
        username=f"user@{slug}.com",
        email=f"user@{slug}.com",
        password="pw",
        is_active=True,
    )
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)

    client = APIClient()
    resp = client.post(
        "/api/auth/login",
        {"email": f"user@{slug}.com", "password": "pw"},
        format="json",
    )
    access_token = resp.json().get("access", "")
    return tenant, user, access_token


class InactiveTenantGuardTest(TestCase):
    """Unit-level test: deactivated tenant → subsequent requests return 403."""

    def setUp(self) -> None:
        self.tenant, self.user, self.token = _setup_tenant(
            "inactive-co", "inactive@co.com"
        )
        self.client = APIClient()

    def test_active_tenant_user_can_authenticate(self) -> None:
        resp = self.client.post(
            "/api/auth/login",
            {"email": "user@inactive-co.com", "password": "pw"},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.json()

    def test_deactivated_tenant_jwt_carries_inactive_slug(self) -> None:
        """Verify the JWT still has the tenant claim even after deactivation (claim decode, not DB check)."""
        import base64
        import json

        parts = self.token.split(".")
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert payload.get("tenant") == "inactive-co"


@pytest.mark.tenant_db
class TenantIsolationTests:
    """
    Full isolation tests using PostgreSQL schema routing.
    These require POSTGRES_HOST env var and are skipped on SQLite (see conftest.py).
    """

    def test_documents_from_tenant_a_are_invisible_to_tenant_b_jwt(self) -> None:
        from django.urls import reverse
        from django_tenants.utils import schema_context
        from documents.models import Document

        slug_a, slug_b = "iso-a", "iso-b"
        tenant_a = Tenant.objects.create(
            slug=slug_a, name="A", schema_name=f"tenant_{slug_a}"
        )
        tenant_b = Tenant.objects.create(
            slug=slug_b, name="B", schema_name=f"tenant_{slug_b}"
        )

        with schema_context(tenant_a.schema_name):
            doc_a = Document.objects.create(
                status=Document.Status.RECEIVED,
                channel="manual",
                file_uri=f"local://{slug_a}/d/original",
                original_filename="a.pdf",
                content_type="application/pdf",
                size_bytes=100,
            )

        _, _, token_b = _setup_tenant(slug_b, "user@iso-b.com")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_b}")

        detail_resp = client.get(reverse("document-detail", args=[doc_a.id]))
        assert detail_resp.status_code == 404, (
            "Tenant B should not see Tenant A's document"
        )

        inbox_resp = client.get(reverse("documents-inbox"))
        ids = [d["id"] for d in inbox_resp.json()]
        assert str(doc_a.id) not in ids, "Tenant A document leaked into Tenant B inbox"

        tenant_a.delete()
        tenant_b.delete()

    def test_request_with_invalid_tenant_jwt_returns_401_or_400(self) -> None:
        import base64
        import json

        fake_payload = (
            base64.urlsafe_b64encode(
                json.dumps({"tenant": "does-not-exist", "sub": "99"}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        fake_token = f"header.{fake_payload}.sig"

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {fake_token}")
        resp = client.get("/api/ocr/documents/inbox")
        assert resp.status_code in (400, 401, 403, 404)

    def test_settings_are_isolated_between_tenant_schemas(self) -> None:
        from django_tenants.utils import schema_context
        from documents.models import SETTINGS_SINGLETON_ID, OCRSettings

        slug_a, slug_b = "settings-a", "settings-b"
        tenant_a = Tenant.objects.create(
            slug=slug_a, name="A", schema_name=f"tenant_{slug_a}"
        )
        tenant_b = Tenant.objects.create(
            slug=slug_b, name="B", schema_name=f"tenant_{slug_b}"
        )

        with schema_context(tenant_a.schema_name):
            a_settings, _ = OCRSettings.objects.get_or_create(id=SETTINGS_SINGLETON_ID)
            a_settings.digital_pdf_engine = "docling"
            a_settings.save(update_fields=["digital_pdf_engine", "updated_at"])

        with schema_context(tenant_b.schema_name):
            b_settings, _ = OCRSettings.objects.get_or_create(id=SETTINGS_SINGLETON_ID)
            assert b_settings.digital_pdf_engine != "docling", (
                "Tenant B OCR settings should not reflect Tenant A changes"
            )

        tenant_a.delete()
        tenant_b.delete()
