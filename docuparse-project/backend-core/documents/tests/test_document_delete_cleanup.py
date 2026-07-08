"""Ao apagar um Document, o sinal post_delete remove os objetos do storage
(binário + raw_text.json), evitando órfãos no MinIO/disco. E o comando
``reconcile_storage`` detecta referências pendentes e objetos órfãos.
"""

from __future__ import annotations

import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from docuparse_storage import get_storage

from documents.models import Document, Tenant


def _new_document(tenant, storage_dir):
    """Cria um Document com dois objetos reais gravados no storage local."""
    storage = get_storage(local_dir=storage_dir)
    original = storage.put_bytes("documents/t/doc/original", b"%PDF fake")
    raw = storage.put_bytes("documents/t/doc/ocr/raw_text.json", b'{"raw_text": "x"}')
    document = Document.objects.create(
        tenant=tenant,
        channel="manual",
        file_uri=original.uri,
        raw_text_uri=raw.uri,
        original_filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=9,
    )
    return document, storage, original, raw


class DocumentDeleteCleanupTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="t-del", name="Tenant Del")

    def test_delete_removes_storage_objects(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ):
            document, storage, original, raw = _new_document(self.tenant, storage_dir)
            assert storage.exists(original.uri) is True
            assert storage.exists(raw.uri) is True

            # on_commit só dispara após o commit; captura e executa no teste.
            with self.captureOnCommitCallbacks(execute=True):
                document.delete()

            assert storage.exists(original.uri) is False
            assert storage.exists(raw.uri) is False

    def test_delete_without_uris_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ):
            document = Document.objects.create(
                tenant=self.tenant, channel="manual", file_uri="", raw_text_uri=""
            )
            with self.captureOnCommitCallbacks(execute=True):
                document.delete()  # não deve levantar


class ReconcileStorageCommandTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="t-rec", name="Tenant Rec")

    def test_reports_dangling_reference(self) -> None:
        """Document aponta para um objeto que não existe no storage."""
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ):
            Document.objects.create(
                tenant=self.tenant,
                channel="manual",
                file_uri="local://documents/t/ghost/original",  # nunca gravado
            )
            out = StringIO()
            call_command("reconcile_storage", "--direction", "db-to-storage", stdout=out)
            output = out.getvalue()
            assert "Referências pendentes (banco → storage): 1" in output
            assert "documents/t/ghost/original" in output

    def test_reports_and_deletes_orphan_object(self) -> None:
        """Objeto no storage cujo document_id não existe no banco."""
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ):
            storage = get_storage(local_dir=storage_dir)
            # document_id é UUID (nenhum Document com esse id existe → órfão)
            orphan_id = "11111111-1111-1111-1111-111111111111"
            orphan = storage.put_bytes(f"documents/t/{orphan_id}/original", b"x")
            assert storage.exists(orphan.uri) is True

            out = StringIO()
            call_command(
                "reconcile_storage",
                "--direction",
                "storage-to-db",
                "--delete-orphans",
                stdout=out,
            )
            output = out.getvalue()
            assert "Objetos órfãos (storage → banco): 1" in output
            assert storage.exists(orphan.uri) is False  # removido pelo --delete-orphans

    def test_clean_state_reports_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ):
            out = StringIO()
            call_command("reconcile_storage", stdout=out)
            assert "Consistente" in out.getvalue()
