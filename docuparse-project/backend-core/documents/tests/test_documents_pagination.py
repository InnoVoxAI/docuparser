"""Testes da paginação/busca de `GET /documents` e da auth de
`GET /documents/{id}/file` (feature 009).

Cobrem:
- T004: envelope paginado, cap de `page_size`, navegação, `count`/`total_pages`,
  lista vazia, 401 sem auth, 403 sem permissão.
- T005: filtros `status` (single/CSV), busca por nome/status/tipo/canal e por
  valores de `extraction_result.fields`, mapeamento de rótulos de status.
- T013: dual-auth do endpoint de arquivo (JWT+permissão, token interno, 401, 404).
"""

from __future__ import annotations

import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from docuparse_storage import LocalStorage, document_original_key

from documents.models import (
    Document,
    ExtractionResult,
    Tenant,
    UserProfile,
)
from users.models import Permission, Role


def _grant_inbox_view(user, tenant):
    permission = Permission.objects.create(code="inbox.view", description="Inbox view")
    role = Role.objects.create(name="Operador")
    role.permissions.add(permission)
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)


def _make_document(tenant, *, status=Document.Status.RECEIVED, filename="doc.pdf",
                   channel="manual", document_type="", fields=None):
    document = Document.objects.create(
        tenant=tenant,
        status=status,
        channel=channel,
        file_uri="local://doc",
        original_filename=filename,
        content_type="application/pdf",
        document_type=document_type,
        size_bytes=128,
    )
    if fields is not None:
        ExtractionResult.objects.create(
            document=document,
            schema_id="s",
            schema_version="v1",
            fields=fields,
            confidence=0.9,
        )
    return document


class DocumentsPaginationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="t-pag", name="Tenant Paginação")
        self.user = get_user_model().objects.create_user(username="op", password="x")
        _grant_inbox_view(self.user, self.tenant)
        self.client.force_authenticate(user=self.user)

    def _seed(self, n: int) -> None:
        for i in range(n):
            _make_document(self.tenant, filename=f"doc-{i:03d}.pdf")

    # --- T004: contrato do envelope paginado ---

    def test_response_is_paginated_envelope(self) -> None:
        self._seed(3)
        response = self.client.get(reverse("documents-inbox"))
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= {"results", "count", "page", "page_size", "total_pages"}
        assert data["count"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 25
        assert data["total_pages"] == 1
        assert len(data["results"]) == 3

    def test_page_size_is_capped_at_25(self) -> None:
        self._seed(30)
        response = self.client.get(reverse("documents-inbox"), {"page_size": 100})
        data = response.json()
        assert data["page_size"] == 25
        assert len(data["results"]) == 25
        assert data["count"] == 30
        assert data["total_pages"] == 2

    def test_navigation_between_pages(self) -> None:
        self._seed(30)
        page1 = self.client.get(reverse("documents-inbox"), {"page": 1}).json()
        page2 = self.client.get(reverse("documents-inbox"), {"page": 2}).json()
        assert len(page1["results"]) == 25
        assert len(page2["results"]) == 5
        assert page2["page"] == 2
        ids1 = {d["id"] for d in page1["results"]}
        ids2 = {d["id"] for d in page2["results"]}
        assert ids1.isdisjoint(ids2)

    def test_empty_list_returns_coherent_envelope(self) -> None:
        response = self.client.get(reverse("documents-inbox"))
        data = response.json()
        assert data["results"] == []
        assert data["count"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0

    def test_requires_authentication(self) -> None:
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("documents-inbox"))
        assert response.status_code == 401

    def test_requires_permission(self) -> None:
        other = get_user_model().objects.create_user(username="noperm", password="x")
        self.client.force_authenticate(user=other)
        response = self.client.get(reverse("documents-inbox"))
        assert response.status_code == 403

    # --- T005: filtros e busca ---

    def test_status_single_filter(self) -> None:
        _make_document(self.tenant, status=Document.Status.APPROVED, filename="a.pdf")
        _make_document(self.tenant, status=Document.Status.RECEIVED, filename="b.pdf")
        data = self.client.get(reverse("documents-inbox"), {"status": "APPROVED"}).json()
        assert data["count"] == 1
        assert data["results"][0]["status"] == "APPROVED"

    def test_status_csv_filter_buckets(self) -> None:
        _make_document(self.tenant, status=Document.Status.RECEIVED, filename="a.pdf")
        _make_document(self.tenant, status=Document.Status.OCR_COMPLETED, filename="b.pdf")
        _make_document(self.tenant, status=Document.Status.APPROVED, filename="c.pdf")
        data = self.client.get(
            reverse("documents-inbox"),
            {"status": "RECEIVED,OCR_COMPLETED"},
        ).json()
        assert data["count"] == 2
        returned = {d["status"] for d in data["results"]}
        assert returned == {"RECEIVED", "OCR_COMPLETED"}

    def test_search_by_filename(self) -> None:
        _make_document(self.tenant, filename="nota-fiscal-123.pdf")
        _make_document(self.tenant, filename="boleto.pdf")
        data = self.client.get(reverse("documents-inbox"), {"search": "nota-fiscal"}).json()
        assert data["count"] == 1
        assert "nota-fiscal" in data["results"][0]["original_filename"]

    def test_search_by_document_type_and_channel(self) -> None:
        _make_document(self.tenant, filename="x.pdf", document_type="boleto", channel="email")
        _make_document(self.tenant, filename="y.pdf", document_type="nota", channel="manual")
        by_type = self.client.get(reverse("documents-inbox"), {"search": "boleto"}).json()
        assert by_type["count"] == 1
        by_channel = self.client.get(reverse("documents-inbox"), {"search": "email"}).json()
        assert by_channel["count"] == 1

    def test_search_inside_extraction_fields(self) -> None:
        _make_document(
            self.tenant,
            filename="generic.pdf",
            fields={"fornecedor": {"value": "ACME Distribuidora", "confidence": 0.95}},
        )
        _make_document(self.tenant, filename="other.pdf", fields={"x": {"value": "zzz"}})
        data = self.client.get(reverse("documents-inbox"), {"search": "ACME"}).json()
        assert data["count"] == 1
        assert data["results"][0]["original_filename"] == "generic.pdf"

    def test_search_maps_status_label(self) -> None:
        _make_document(self.tenant, status=Document.Status.APPROVED, filename="a.pdf")
        _make_document(self.tenant, status=Document.Status.RECEIVED, filename="b.pdf")
        data = self.client.get(reverse("documents-inbox"), {"search": "aprovado"}).json()
        assert data["count"] >= 1
        assert any(d["status"] == "APPROVED" for d in data["results"])

    def test_search_resets_to_full_set(self) -> None:
        # Busca atua sobre todo o conjunto, não só a página atual.
        for i in range(30):
            _make_document(self.tenant, filename=f"doc-{i:03d}.pdf")
        _make_document(self.tenant, filename="unique-marker.pdf")
        data = self.client.get(reverse("documents-inbox"), {"search": "unique-marker"}).json()
        assert data["count"] == 1


class DocumentFileAuthTests(TestCase):
    """T013 — dual-auth do endpoint de arquivo."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="t-file", name="Tenant File")
        self.user = get_user_model().objects.create_user(username="fileop", password="x")
        _grant_inbox_view(self.user, self.tenant)
        self.document = _make_document(self.tenant, filename="orig.pdf")

    def _store_file(self, storage_dir: str) -> None:
        stored = LocalStorage(storage_dir).put_bytes(
            document_original_key(self.tenant.slug, str(self.document.id)),
            b"%PDF original",
        )
        self.document.file_uri = stored.uri
        self.document.save(update_fields=["file_uri"])

    def test_user_with_permission_gets_file(self) -> None:
        self.client.force_authenticate(user=self.user)
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            self._store_file(storage_dir)
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"%PDF original"

    def test_user_without_permission_is_forbidden(self) -> None:
        other = get_user_model().objects.create_user(username="nofileperm", password="x")
        self.client.force_authenticate(user=other)
        response = self.client.get(reverse("document-file", args=[self.document.id]))
        assert response.status_code == 403

    def test_internal_service_token_gets_file(self) -> None:
        token = "internal-secret"
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir,
            DOCUPARSE_INTERNAL_SERVICE_TOKEN=token,
        ):
            self._store_file(storage_dir)
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 200

    def test_no_credentials_is_unauthorized(self) -> None:
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN="some-token"):
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 401

    def test_missing_file_returns_404(self) -> None:
        self.client.force_authenticate(user=self.user)
        with tempfile.TemporaryDirectory() as storage_dir, self.settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 404
