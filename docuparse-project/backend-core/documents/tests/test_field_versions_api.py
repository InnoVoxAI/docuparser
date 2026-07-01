"""Integration tests for the field versions API (T009/T014/T016/T020)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import (
    Document,
    ExtractionFieldVersion,
    ExtractionResult,
    Tenant,
    UserProfile,
)
from documents.services import field_versioning as fv
from users.models import Permission, Role


def _grant_validation(user, tenant):
    permission = Permission.objects.create(code="documents.validate", description="Validate")
    role = Role.objects.create(name="Validador")
    role.permissions.add(permission)
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)


class FieldVersionsApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="t-api", name="Tenant API")
        self.user = get_user_model().objects.create_user(username="val", password="x")
        _grant_validation(self.user, self.tenant)
        self.client.force_authenticate(user=self.user)

        self.document = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.EXTRACTION_COMPLETED,
            channel="manual",
            file_uri="local://doc",
            content_type="application/pdf",
            size_bytes=10,
        )
        self.extraction = ExtractionResult.objects.create(
            document=self.document,
            schema_id="s",
            schema_version="v1",
            fields={"valor": {"value": "100", "confidence": 0.8}},
            confidence=0.8,
        )
        self.v1 = fv.create_version(
            self.document,
            fields={"valor": {"value": "100", "confidence": 0.8}},
            source_type=ExtractionFieldVersion.SourceType.INITIAL_EXTRACTION,
        )

    def _save_url(self):
        return reverse("document-save-fields", args=[self.document.id])

    def _history_url(self):
        return reverse("document-field-versions", args=[self.document.id])

    # ----- T009: PUT /fields -----

    def test_save_creates_new_active_version_and_syncs_result(self) -> None:
        response = self.client.put(
            self._save_url(),
            {"base_version_number": 1, "fields": [{"name": "valor", "value": "200"}]},
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["version_number"] == 2
        assert body["is_active"] is True
        assert body["fields"]["valor"]["confidence"] == 1.0
        self.extraction.refresh_from_db()
        assert self.extraction.fields["valor"]["value"] == "200"

    def test_save_with_stale_base_version_returns_409(self) -> None:
        fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
        )
        response = self.client.put(
            self._save_url(),
            {"base_version_number": 1, "fields": [{"name": "valor", "value": "300"}]},
            format="json",
        )
        assert response.status_code == 409
        assert response.json()["active_version_number"] == 2
        assert ExtractionFieldVersion.objects.filter(document=self.document).count() == 2

    def test_save_empty_list_returns_422(self) -> None:
        response = self.client.put(
            self._save_url(),
            {"base_version_number": 1, "fields": []},
            format="json",
        )
        assert response.status_code == 422

    def test_save_without_permission_returns_403(self) -> None:
        other = get_user_model().objects.create_user(username="noperm", password="x")
        client = APIClient()
        client.force_authenticate(user=other)
        response = client.put(
            self._save_url(),
            {"base_version_number": 1, "fields": [{"name": "valor", "value": "200"}]},
            format="json",
        )
        assert response.status_code == 403

    # ----- T014: remoção (US2) -----

    def test_save_with_removed_field_excludes_it_and_preserves_history(self) -> None:
        v2 = fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "100"}, {"name": "extra", "value": "x"}],
            base_version_number=1,
        )
        response = self.client.put(
            self._save_url(),
            {"base_version_number": v2.version_number, "fields": [{"name": "valor", "value": "100"}]},
            format="json",
        )
        assert response.status_code == 201
        assert "extra" not in response.json()["fields"]
        v2.refresh_from_db()
        assert "extra" in v2.fields  # versão anterior preservada

    # ----- T016: GET /field-versions (US3) -----

    def test_history_lists_all_versions_desc_readonly(self) -> None:
        fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
        )
        response = self.client.get(self._history_url())
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert body["active_version_number"] == 2
        numbers = [v["version_number"] for v in body["results"]]
        assert numbers == [2, 1]  # desc

    def test_history_get_does_not_allow_post(self) -> None:
        response = self.client.post(self._history_url(), {}, format="json")
        assert response.status_code == 405  # somente leitura

    # ----- T020: validate cria versão MANUAL_EDIT -----

    def test_validate_with_corrected_fields_creates_manual_version(self) -> None:
        url = reverse("document-validate", args=[self.document.id])
        response = self.client.post(
            url,
            {
                "decision": "corrected",
                "decided_by_id": str(self.user.id),
                "corrected_fields": {"valor": "555"},
            },
            format="json",
        )
        assert response.status_code == 201
        active = fv.get_active_version(self.document)
        assert active.source_type == ExtractionFieldVersion.SourceType.MANUAL_EDIT
        assert active.fields["valor"]["value"] == "555"
        # versão inicial preservada
        assert ExtractionFieldVersion.objects.filter(document=self.document, version_number=1).exists()
