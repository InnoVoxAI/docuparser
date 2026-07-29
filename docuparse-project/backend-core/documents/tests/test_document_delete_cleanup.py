"""Ao apagar um Document, o sinal post_delete remove os objetos do storage
(binário + raw_text.json), evitando órfãos no MinIO/disco. E o comando
``reconcile_storage`` detecta referências pendentes e objetos órfãos.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from docuparse_storage import get_storage
from tenants.models import Tenant

from documents.models import Document


def _new_document(storage_dir):
    """Cria um Document com dois objetos reais gravados no storage local."""
    storage = get_storage()
    original = storage.put_bytes("documents/t/doc/original", b"%PDF fake")
    raw = storage.put_bytes("documents/t/doc/ocr/raw_text.json", b'{"raw_text": "x"}')
    document = Document.objects.create(
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
        # A unique slug per test method: Tenant.save()'s schema creation runs
        # its own nested migrate, which commits independently of this test's
        # transaction rollback — reusing a slug would resurrect a schema with
        # data left over from a previous test method.
        self.tenant = Tenant.objects.create(
            slug=f"t-del-{uuid.uuid4().hex[:8]}", name="Tenant Del"
        )
        connection.set_tenant(self.tenant)

    def test_delete_removes_storage_objects(self) -> None:
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            # get_storage() reads DOCUPARSE_STORAGE_BACKEND from the process
            # environment, not Django settings: overriding just the local dir
            # is not enough to escape the real S3/MinIO backend the
            # devcontainer's .env pins by default.
            mock.patch.dict(
                os.environ,
                {
                    "DOCUPARSE_STORAGE_BACKEND": "local",
                    "DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir,
                },
            ),
            override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            document, storage, original, raw = _new_document(storage_dir)
            assert storage.exists(original.uri) is True
            assert storage.exists(raw.uri) is True

            # on_commit só dispara após o commit; captura e executa no teste.
            with self.captureOnCommitCallbacks(execute=True):
                document.delete()

            assert storage.exists(original.uri) is False
            assert storage.exists(raw.uri) is False

    def test_delete_without_uris_is_noop(self) -> None:
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            # get_storage() reads DOCUPARSE_STORAGE_BACKEND from the process
            # environment, not Django settings: overriding just the local dir
            # is not enough to escape the real S3/MinIO backend the
            # devcontainer's .env pins by default.
            mock.patch.dict(
                os.environ,
                {
                    "DOCUPARSE_STORAGE_BACKEND": "local",
                    "DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir,
                },
            ),
            override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            document = Document.objects.create(
                channel="manual", file_uri="", raw_text_uri=""
            )
            with self.captureOnCommitCallbacks(execute=True):
                document.delete()  # não deve levantar


class ReconcileStorageCommandTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(
            slug=f"t-rec-{uuid.uuid4().hex[:8]}", name="Tenant Rec"
        )
        connection.set_tenant(self.tenant)

    def test_reports_dangling_reference(self) -> None:
        """Document aponta para um objeto que não existe no storage."""
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            # get_storage() reads DOCUPARSE_STORAGE_BACKEND from the process
            # environment, not Django settings: overriding just the local dir
            # is not enough to escape the real S3/MinIO backend the
            # devcontainer's .env pins by default.
            mock.patch.dict(
                os.environ,
                {
                    "DOCUPARSE_STORAGE_BACKEND": "local",
                    "DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir,
                },
            ),
            override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            Document.objects.create(
                channel="manual",
                file_uri="local://documents/t/ghost/original",  # nunca gravado
            )
            out = StringIO()
            call_command(
                "reconcile_storage", "--direction", "db-to-storage", stdout=out
            )
            output = out.getvalue()
            assert "Referências pendentes (banco → storage): 1" in output
            assert "documents/t/ghost/original" in output

    def test_reports_and_deletes_orphan_object(self) -> None:
        """Objeto no storage cujo document_id não existe no banco."""
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            # get_storage() reads DOCUPARSE_STORAGE_BACKEND from the process
            # environment, not Django settings: overriding just the local dir
            # is not enough to escape the real S3/MinIO backend the
            # devcontainer's .env pins by default.
            mock.patch.dict(
                os.environ,
                {
                    "DOCUPARSE_STORAGE_BACKEND": "local",
                    "DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir,
                },
            ),
            override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            storage = get_storage()
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
        with (
            tempfile.TemporaryDirectory() as storage_dir,
            # get_storage() reads DOCUPARSE_STORAGE_BACKEND from the process
            # environment, not Django settings: overriding just the local dir
            # is not enough to escape the real S3/MinIO backend the
            # devcontainer's .env pins by default.
            mock.patch.dict(
                os.environ,
                {
                    "DOCUPARSE_STORAGE_BACKEND": "local",
                    "DOCUPARSE_LOCAL_STORAGE_DIR": storage_dir,
                },
            ),
            override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir),
        ):
            out = StringIO()
            call_command("reconcile_storage", stdout=out)
            assert "Consistente" in out.getvalue()
