"""Rotas removidas não podem voltar abertas.

AR-01 (revisão de arquitetura 2026-11): ``POST /api/ocr/process`` era uma view
Django pura, com ``@csrf_exempt`` e sem autenticação, que recebia um arquivo e
disparava OCR pago no backend-ocr. Nenhum cliente a usava, e ela foi removida.

AR-07: o ``/admin/`` do Django estava exposto em prod sem uso, e sob gunicorn
ficava sem estáticos. A rota e o app ``django.contrib.admin`` foram removidos.
"""

from __future__ import annotations

from unittest.mock import patch

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import Resolver404, resolve


class RemovedOcrProcessRouteTests(TestCase):
    def test_post_without_credentials_returns_404_and_does_not_call_ocr(self) -> None:
        upload = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4", content_type="application/pdf"
        )
        with patch("documents.services.ocr_client.OCRClient.process_document") as ocr:
            response = self.client.post(
                "/api/ocr/process", {"file": upload, "engine": "openrouter"}
            )
        assert response.status_code == 404
        ocr.assert_not_called()


class RemovedDjangoAdminTests(TestCase):
    def test_admin_urls_do_not_resolve(self) -> None:
        for path in ("/admin/", "/admin/login/"):
            with self.assertRaises(Resolver404):
                resolve(path)

    def test_admin_login_returns_404(self) -> None:
        assert self.client.get("/admin/login/").status_code == 404

    def test_admin_app_not_installed(self) -> None:
        assert not apps.is_installed("django.contrib.admin")
