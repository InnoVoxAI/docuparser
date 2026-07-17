from __future__ import annotations

import base64
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Tenant, UserProfile
from users.models import Role

User = get_user_model()


def _decode_payload(token: str) -> dict:
    parts = token.split(".")
    assert len(parts) == 3, "Not a JWT"
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


class JWTTenantClaimTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        with patch.object(Tenant, "auto_create_schema", new=False):
            self.tenant = Tenant.objects.create(
                slug="acme", name="Acme Corp", schema_name="tenant_acme"
            )
        self.role = Role.objects.create(name="admin")
        self.user = User.objects.create_user(
            username="user@acme.com", email="user@acme.com", password="pw", is_active=True
        )
        UserProfile.objects.create(user=self.user, tenant=self.tenant, role_ref=self.role)

    def test_login_access_token_contains_tenant_slug(self) -> None:
        response = self.client.post(
            "/api/auth/login", {"email": "user@acme.com", "password": "pw"}, format="json"
        )
        assert response.status_code == 200
        payload = _decode_payload(response.json()["access"])
        assert payload.get("tenant") == "acme"

    def test_login_refresh_token_contains_tenant_slug(self) -> None:
        response = self.client.post(
            "/api/auth/login", {"email": "user@acme.com", "password": "pw"}, format="json"
        )
        assert response.status_code == 200
        payload = _decode_payload(response.json()["refresh"])
        assert payload.get("tenant") == "acme"

    def test_user_without_profile_gets_token_without_tenant_claim(self) -> None:
        orphan = User.objects.create_user(
            username="orphan@acme.com", email="orphan@acme.com", password="pw", is_active=True
        )
        response = self.client.post(
            "/api/auth/login", {"email": "orphan@acme.com", "password": "pw"}, format="json"
        )
        assert response.status_code == 200
        payload = _decode_payload(response.json()["access"])
        assert "tenant" not in payload
