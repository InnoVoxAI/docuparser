"""
Integration tests for the tenant admin invite flow (creation, activation, resend).

Tests marked `tenant_db` require POSTGRES_HOST env var (PostgreSQL with
schema routing). Tests without that marker run on any database.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from users.models import Role

from tenants.models import Invite, Tenant
from tenants.tests.test_provisioning import _admin_client

User = get_user_model()

VALID_PASSWORD = "C0rrect-H0rse-Battery"
_TOKEN_RE = re.compile(r"/ativar-conta/([^\s]+)")


def _extract_token(email_body: str) -> str:
    match = _TOKEN_RE.search(email_body)
    assert match is not None, "activation link not found in email body"
    return match.group(1)


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

        invite = Invite.objects.get(user=admin_user, tenant=tenant)
        assert invite.status == Invite.Status.PENDING

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


class InviteActivationTests(TestCase):
    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()
        Role.objects.get_or_create(name="admin")

    def _create_invite(self, slug: str = "acme", email: str = "jane.doe@acme.com"):
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {
                    "slug": slug,
                    "name": "ACME Corporation",
                    "admin_name": "Jane Doe",
                    "admin_email": email,
                },
                format="json",
            )
        assert response.status_code == 201
        token = _extract_token(mail.outbox[-1].body)
        invite = Invite.objects.get(user__username=email)
        return token, invite

    def test_activate_with_valid_token_and_password_succeeds_and_allows_login(
        self,
    ) -> None:
        token, invite = self._create_invite()

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["email"] == "jane.doe@acme.com"
        assert body["data"]["tenant_slug"] == "acme"

        invite.refresh_from_db()
        assert invite.status == Invite.Status.USED
        assert invite.used_at is not None

        admin_user = User.objects.get(username="jane.doe@acme.com")
        assert admin_user.has_usable_password() is True

        login_response = self.client.post(
            "/api/auth/login",
            {"email": "jane.doe@acme.com", "password": VALID_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    def test_activate_with_expired_token_returns_410(self) -> None:
        token, invite = self._create_invite(
            slug="expired-tenant", email="expired@acme.com"
        )
        invite.expires_at = timezone.now() - timezone.timedelta(hours=1)
        invite.save(update_fields=["expires_at"])

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "INVITE_EXPIRED"

    def test_activate_with_already_used_token_returns_410(self) -> None:
        token, invite = self._create_invite(slug="used-tenant", email="used@acme.com")
        invite.status = Invite.Status.USED
        invite.used_at = timezone.now()
        invite.save(update_fields=["status", "used_at"])

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "INVITE_ALREADY_USED"

    def test_activate_with_nonexistent_token_returns_404(self) -> None:
        response = self.client.post(
            "/api/admin/tenants/invites/does-not-exist/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVITE_NOT_FOUND"

    def test_activate_with_invalid_password_returns_400_and_leaves_invite_pending(
        self,
    ) -> None:
        token, invite = self._create_invite(
            slug="weak-password-tenant", email="weak@acme.com"
        )

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": "12345678"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

        invite.refresh_from_db()
        assert invite.status == Invite.Status.PENDING

        admin_user = User.objects.get(username="weak@acme.com")
        assert admin_user.has_usable_password() is False


class InviteResendTests(TestCase):
    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()
        Role.objects.get_or_create(name="admin")

    def _create_invite(self, slug: str = "acme", email: str = "jane.doe@acme.com"):
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {
                    "slug": slug,
                    "name": "ACME Corporation",
                    "admin_name": "Jane Doe",
                    "admin_email": email,
                },
                format="json",
            )
        assert response.status_code == 201
        token = _extract_token(mail.outbox[-1].body)
        invite = Invite.objects.get(user__username=email)
        return token, invite

    def test_resend_invalidates_previous_pending_and_creates_new_pending(
        self,
    ) -> None:
        old_token, old_invite = self._create_invite(
            slug="resend-tenant", email="resend@acme.com"
        )

        response = self.client.post(
            "/api/admin/tenants/resend-tenant/invites/resend/",
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["admin_email"] == "resend@acme.com"
        assert "expires_at" in body["data"]

        old_invite.refresh_from_db()
        assert old_invite.status == Invite.Status.INVALIDATED

        new_invite = (
            Invite.objects.filter(user=old_invite.user).exclude(id=old_invite.id).get()
        )
        assert new_invite.status == Invite.Status.PENDING
        assert new_invite.token_hash != old_invite.token_hash

        new_token = _extract_token(mail.outbox[-1].body)
        assert new_token != old_token

        # the old link no longer works, the new one does
        expired_response = self.client.post(
            f"/api/admin/tenants/invites/{old_token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )
        assert expired_response.status_code == 410

        activate_response = self.client.post(
            f"/api/admin/tenants/invites/{new_token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )
        assert activate_response.status_code == 200

    def test_resend_for_already_active_admin_returns_409(self) -> None:
        token, invite = self._create_invite(
            slug="active-tenant", email="active@acme.com"
        )
        self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        response = self.client.post(
            "/api/admin/tenants/active-tenant/invites/resend/",
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ADMIN_ALREADY_ACTIVE"


class TenantUsersInviteTests(TestCase):
    """FR-016 regression: tenant_users_view (platform operator, `tenants.manage`)
    must invite users instead of creating them with a plaintext password."""

    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()

    def test_create_user_without_password_sends_invite_even_for_platform_role(
        self,
    ) -> None:
        platform_role, _ = Role.objects.get_or_create(
            name="admin", defaults={"is_platform_role": True}
        )
        if not platform_role.is_platform_role:
            platform_role.is_platform_role = True
            platform_role.save(update_fields=["is_platform_role"])

        response = self.client.post(
            f"/api/admin/tenants/{self.tenant.slug}/users/",
            {
                "name": "Recovered Admin",
                "email": "recovered-admin@acme.com",
                "role_id": str(platform_role.id),
            },
            format="json",
        )

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["error"] is None
        assert body["meta"]["invite_sent"] is True

        user = User.objects.get(username="recovered-admin@acme.com")
        assert user.has_usable_password() is False

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["recovered-admin@acme.com"]

    def test_create_user_with_email_already_in_use_returns_409(self) -> None:
        role, _ = Role.objects.get_or_create(name="operator")
        User.objects.create_user(
            username="taken@acme.com", email="taken@acme.com", password="pw"
        )

        response = self.client.post(
            f"/api/admin/tenants/{self.tenant.slug}/users/",
            {
                "name": "Duplicate",
                "email": "taken@acme.com",
                "role_id": str(role.id),
            },
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "USER_EXISTS"
