"""
Integration tests for the generic user invite flow (019-generalize-tenant-invite):
inviting a non-admin user to the caller's own tenant (`POST /api/ocr/users`),
activation, and the FR-015 tenant-resolution regression.

Tests marked `tenant_db` require POSTGRES_HOST env var (PostgreSQL with
schema routing). Tests without that marker run on any database.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient
from tenants.models import Invite, Tenant, UserProfile

from users.models import Permission, Role

User = get_user_model()

VALID_PASSWORD = "C0rrect-H0rse-Battery"
_TOKEN_RE = re.compile(r"/ativar-conta/([^\s]+)")


def _extract_token(email_body: str) -> str:
    match = _TOKEN_RE.search(email_body)
    assert match is not None, "activation link not found in email body"
    return match.group(1)


def _seed_permissions() -> None:
    codes = ["users.manage", "roles.manage", "inbox.view", "documents.validate"]
    for code in codes:
        Permission.objects.get_or_create(code=code, defaults={"description": code})


def _make_tenant_admin_role() -> Role:
    role, _ = Role.objects.get_or_create(name="Admin")
    role.permissions.set(Permission.objects.all())
    return role


def _make_op_role() -> Role:
    role, _ = Role.objects.get_or_create(name="Operador")
    role.permissions.set(
        Permission.objects.filter(code__in=["inbox.view", "documents.validate"])
    )
    return role


def _make_platform_role() -> Role:
    role, _ = Role.objects.get_or_create(
        name="admin", defaults={"is_platform_role": True}
    )
    if not role.is_platform_role:
        role.is_platform_role = True
        role.save(update_fields=["is_platform_role"])
    role.permissions.set(Permission.objects.all())
    return role


def _make_tenant(slug: str, name: str) -> Tenant:
    with patch.object(Tenant, "auto_create_schema", new=False):
        return Tenant.objects.create(slug=slug, name=name, schema_name=f"tenant_{slug}")


def _tenant_admin_client(
    tenant: Tenant, role: Role, email: str = "tadmin@t.com"
) -> tuple[APIClient, User]:
    """Create a tenant admin, log them in for real (so the JWT carries the
    tenant claim JWTTenantMiddleware needs to resolve request.tenant), and
    return an authenticated client."""
    user = User.objects.create_user(
        username=email, email=email, password="pw", is_active=True
    )
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)

    client = APIClient()
    login = client.post(
        "/api/auth/login", {"email": email, "password": "pw"}, format="json"
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client, user


class UserInviteCreateTests(TestCase):
    def setUp(self) -> None:
        _seed_permissions()
        self.tenant = _make_tenant("acme", "ACME Corporation")
        self.admin_role = _make_tenant_admin_role()
        self.op_role = _make_op_role()
        self.client, self.admin_user = _tenant_admin_client(
            self.tenant, self.admin_role
        )

    def test_invite_user_creates_unusable_password_user_in_callers_tenant_and_sends_email(
        self,
    ) -> None:
        response = self.client.post(
            "/api/ocr/users",
            {
                "name": "Maria Silva",
                "email": "maria.silva@acme.com",
                "role_id": str(self.op_role.id),
            },
            format="json",
        )

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["error"] is None
        assert body["meta"]["invite_sent"] is True
        assert body["data"]["email"] == "maria.silva@acme.com"

        user = User.objects.get(username="maria.silva@acme.com")
        assert user.has_usable_password() is False

        profile = UserProfile.objects.get(user=user)
        assert profile.tenant_id == self.tenant.id
        assert profile.role_ref_id == self.op_role.id

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["maria.silva@acme.com"]

    def test_invite_user_with_platform_role_returns_400(self) -> None:
        platform_role = _make_platform_role()

        response = self.client.post(
            "/api/ocr/users",
            {
                "name": "Maria Silva",
                "email": "maria.silva@acme.com",
                "role_id": str(platform_role.id),
            },
            format="json",
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert not User.objects.filter(username="maria.silva@acme.com").exists()

    def test_invite_user_with_email_already_in_use_returns_409(self) -> None:
        User.objects.create_user(
            username="taken@acme.com", email="taken@acme.com", password="pw"
        )

        response = self.client.post(
            "/api/ocr/users",
            {
                "name": "Maria Silva",
                "email": "taken@acme.com",
                "role_id": str(self.op_role.id),
            },
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "USER_EXISTS"

    def test_invite_user_from_second_tenant_assigns_correct_tenant_not_first_in_db(
        self,
    ) -> None:
        """Regression test for FR-015: the invited user must land in
        request.tenant (the caller's tenant), not Tenant.objects.first()."""
        second_tenant = _make_tenant("beta", "Beta Corp")
        # Tenant.Meta.ordering = ["name"]; "acme" sorts before "beta", so
        # Tenant.objects.first() — the pre-fix bug's hardcoded target — is
        # NOT this tenant. That's the scenario the bug silently mishandled.
        assert second_tenant.pk != Tenant.objects.first().pk

        second_admin_role = _make_tenant_admin_role()
        second_op_role = _make_op_role()
        second_client, _ = _tenant_admin_client(
            second_tenant, second_admin_role, email="tadmin2@beta.com"
        )

        response = second_client.post(
            "/api/ocr/users",
            {
                "name": "Carlos Souza",
                "email": "carlos.souza@beta.com",
                "role_id": str(second_op_role.id),
            },
            format="json",
        )

        assert response.status_code == 201, response.content
        profile = UserProfile.objects.get(user__username="carlos.souza@beta.com")
        assert profile.tenant_id == second_tenant.id
        assert profile.tenant_id != Tenant.objects.first().pk


class UserInviteActivationTests(TestCase):
    def setUp(self) -> None:
        _seed_permissions()
        self.tenant = _make_tenant("acme", "ACME Corporation")
        self.admin_role = _make_tenant_admin_role()
        self.op_role = _make_op_role()
        self.client, self.admin_user = _tenant_admin_client(
            self.tenant, self.admin_role
        )

    def _invite_user(
        self, email: str = "maria.silva@acme.com", name: str = "Maria Silva"
    ) -> str:
        response = self.client.post(
            "/api/ocr/users",
            {"name": name, "email": email, "role_id": str(self.op_role.id)},
            format="json",
        )
        assert response.status_code == 201, response.content
        return _extract_token(mail.outbox[-1].body)

    def test_activate_invited_user_sets_password_marks_invite_used_and_allows_login(
        self,
    ) -> None:
        token = self._invite_user()

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 200, response.content
        body = response.json()
        assert body["data"]["email"] == "maria.silva@acme.com"
        assert body["data"]["tenant_slug"] == "acme"

        user = User.objects.get(username="maria.silva@acme.com")
        assert user.has_usable_password() is True

        invite = Invite.objects.get(user=user)
        assert invite.status == Invite.Status.USED

        login_response = APIClient().post(
            "/api/auth/login",
            {"email": "maria.silva@acme.com", "password": VALID_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200
        assert login_response.data["user"]["role"]["name"] == self.op_role.name

    def test_activate_with_already_used_token_returns_410(self) -> None:
        token = self._invite_user(email="used@acme.com", name="Used User")
        self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "INVITE_ALREADY_USED"

    def test_activate_with_expired_token_returns_410(self) -> None:
        token = self._invite_user(email="expired@acme.com", name="Expired User")
        invite = Invite.objects.get(user__username="expired@acme.com")

        from django.utils import timezone

        invite.expires_at = timezone.now() - timezone.timedelta(hours=1)
        invite.save(update_fields=["expires_at"])

        response = self.client.post(
            f"/api/admin/tenants/invites/{token}/activate/",
            {"password": VALID_PASSWORD},
            format="json",
        )

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "INVITE_EXPIRED"


class UserInviteResendTests(TestCase):
    def setUp(self) -> None:
        _seed_permissions()
        self.tenant = _make_tenant("acme", "ACME Corporation")
        self.admin_role = _make_tenant_admin_role()
        self.op_role = _make_op_role()
        self.client, self.admin_user = _tenant_admin_client(
            self.tenant, self.admin_role
        )

    def _invite_user(
        self, email: str = "maria.silva@acme.com", name: str = "Maria Silva"
    ) -> User:
        response = self.client.post(
            "/api/ocr/users",
            {"name": name, "email": email, "role_id": str(self.op_role.id)},
            format="json",
        )
        assert response.status_code == 201, response.content
        return User.objects.get(username=email)

    def test_resend_invalidates_previous_pending_invite_and_issues_new_one(
        self,
    ) -> None:
        user = self._invite_user()
        old_invite = Invite.objects.get(user=user)
        old_token_hash = old_invite.token_hash

        response = self.client.post(
            f"/api/ocr/users/{user.pk}/invites/resend/",
            format="json",
        )

        assert response.status_code == 200, response.content
        body = response.json()
        assert body["error"] is None
        assert body["data"]["email"] == user.email

        old_invite.refresh_from_db()
        assert old_invite.status == Invite.Status.INVALIDATED

        new_invite = Invite.objects.exclude(id=old_invite.id).get(user=user)
        assert new_invite.status == Invite.Status.PENDING
        assert new_invite.token_hash != old_token_hash
        assert new_invite.expires_at != old_invite.expires_at

        assert len(mail.outbox) == 2

    def test_resend_for_user_in_another_tenant_returns_404(self) -> None:
        other_tenant = _make_tenant("beta", "Beta Corp")
        other_role = _make_op_role()
        other_user = User.objects.create_user(
            username="outsider@beta.com",
            email="outsider@beta.com",
            is_active=True,
        )
        other_user.set_unusable_password()
        other_user.save()
        UserProfile.objects.create(
            user=other_user, tenant=other_tenant, role_ref=other_role
        )

        response = self.client.post(
            f"/api/ocr/users/{other_user.pk}/invites/resend/",
            format="json",
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "USER_NOT_FOUND"

    def test_resend_for_already_active_user_returns_409(self) -> None:
        user = self._invite_user(email="active@acme.com", name="Active User")
        user.set_password(VALID_PASSWORD)
        user.save()

        response = self.client.post(
            f"/api/ocr/users/{user.pk}/invites/resend/",
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "USER_ALREADY_ACTIVE"
