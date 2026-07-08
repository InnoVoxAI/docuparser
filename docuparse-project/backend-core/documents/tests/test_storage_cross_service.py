"""US1 (T010) — o arquivo original gravado por um serviço (ex.: ingestão, via
S3) é servido pelo endpoint /documents/{id}/file de outro "pod", com o
content_type preservado (FR-009, SC-002).
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from moto import mock_aws
from rest_framework.test import APIClient

from docuparse_storage import document_original_key, get_storage

from documents.models import Document, Tenant
from documents.tests._storage_env import create_test_bucket, s3_test_env, s3_uri
from documents.tests.test_documents_pagination import _grant_inbox_view, _make_document


class DocumentFileContentTypeTests(TestCase):
    """FR-009 — o content_type servido ao navegador é o do documento (do banco)."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="t-ct", name="Tenant CT")
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(username="ctop", password="x")
        _grant_inbox_view(self.user, self.tenant)
        self.client.force_authenticate(user=self.user)

    def test_served_content_type_matches_document(self) -> None:
        from django.test import override_settings

        document = _make_document(self.tenant, filename="orig.pdf")  # content_type application/pdf
        import tempfile

        with tempfile.TemporaryDirectory() as storage_dir, override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir):
            stored = get_storage(local_dir=storage_dir).put_bytes(
                document_original_key(self.tenant.slug, str(document.id)), b"%PDF orig"
            )
            document.file_uri = stored.uri
            document.save(update_fields=["file_uri"])
            response = self.client.get(reverse("document-file", args=[document.id]))
            assert response.status_code == 200
            assert response["Content-Type"] == "application/pdf"


class DocumentFileCrossServiceS3Tests(TestCase):
    """US1/SC-002 — arquivo gravado via S3 por um serviço é servido por outro pod."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="t-x", name="Tenant Cross")
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(username="xop", password="x")
        _grant_inbox_view(self.user, self.tenant)
        self.client.force_authenticate(user=self.user)
        self.document = _make_document(self.tenant, filename="orig.pdf")

    @mock_aws
    def test_serves_file_written_by_another_service_via_s3(self) -> None:
        create_test_bucket()
        with s3_test_env():
            # Serviço A (ingestão) grava o original no S3.
            key = document_original_key(self.tenant.slug, str(self.document.id))
            stored = get_storage().put_bytes(key, b"%PDF from-another-pod")
            assert stored.uri.startswith("s3://")
            self.document.file_uri = stored.uri
            self.document.save(update_fields=["file_uri"])

            # Serviço B (core) serve /file — deve ler do S3 (outro pod) e casar bytes/type.
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"%PDF from-another-pod"
            assert response["Content-Type"] == "application/pdf"

    @mock_aws
    def test_missing_s3_object_returns_404(self) -> None:
        create_test_bucket()
        with s3_test_env():
            self.document.file_uri = s3_uri(document_original_key(self.tenant.slug, str(self.document.id)))
            self.document.save(update_fields=["file_uri"])
            response = self.client.get(reverse("document-file", args=[self.document.id]))
            assert response.status_code == 404
