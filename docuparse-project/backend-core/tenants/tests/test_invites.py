"""
Integration tests for the tenant admin invite flow (creation, activation, resend).

Tests marked `tenant_db` require POSTGRES_HOST env var (PostgreSQL with
schema routing). Tests without that marker run on any database.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from users.models import Role

from tenants.models import Tenant, TenantAdminInvite
from tenants.tests.test_provisioning import _admin_client

User = get_user_model()


class TenantCreateAdminInviteTests(TestCase):
    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()
        Role.objects.get_or_create(name="admin")

    def test_create_tenant_creates_admin_user_profile_and_invite(self) -> None:
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {
                    "slug": "acme",
                    "name": "ACME Corporation",
                    "admin_name": "Jane Doe",
                    "admin_email": "jane.doe@acme.com",
                },
                format="json",
            )

        assert response.status_code == 201
        assert response.json()["meta"]["admin_invite_sent"] is True

        tenant = Tenant.objects.get(slug="acme")
        admin_user = User.objects.get(username="jane.doe@acme.com")
        assert admin_user.first_name == "Jane Doe"
        assert not admin_user.has_usable_password()

        profile = admin_user.docuparse_profile
        assert profile.tenant_id == tenant.id
        assert profile.role_ref.name == "admin"

        invite = TenantAdminInvite.objects.get(user=admin_user, tenant=tenant)
        assert invite.status == TenantAdminInvite.Status.PENDING

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["jane.doe@acme.com"]

    def test_create_tenant_with_missing_admin_email_returns_400(self) -> None:
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {"slug": "no-admin", "name": "No Admin", "admin_name": "Jane Doe"},
                format="json",
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert not Tenant.objects.filter(slug="no-admin").exists()

    def test_create_tenant_with_invalid_admin_email_returns_400(self) -> None:
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {
                    "slug": "bad-admin-email",
                    "name": "Bad Admin Email",
                    "admin_name": "Jane Doe",
                    "admin_email": "not-an-email",
                },
                format="json",
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert not Tenant.objects.filter(slug="bad-admin-email").exists()

    def test_create_tenant_with_admin_email_in_use_returns_409(self) -> None:
        User.objects.create_user(
            username="taken@acme.com", email="taken@acme.com", password="pw"
        )
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {
                    "slug": "dup-admin-email",
                    "name": "Dup Admin Email",
                    "admin_name": "Jane Doe",
                    "admin_email": "taken@acme.com",
                },
                format="json",
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ADMIN_EMAIL_IN_USE"
        assert not Tenant.objects.filter(slug="dup-admin-email").exists()
