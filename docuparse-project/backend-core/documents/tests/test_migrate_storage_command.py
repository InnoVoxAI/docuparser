"""O management command ``migrate_storage_local_to_s3`` copia os artefatos
local:// para o S3/MinIO e atualiza as URIs no banco (feature 011)."""

from __future__ import annotations

import tempfile
from io import StringIO

import boto3
from django.core.management import call_command
from django.test import TestCase, override_settings
from moto import mock_aws

from docuparse_storage import LocalStorage

from documents.models import Document, Tenant
from documents.tests._storage_env import create_test_bucket, s3_bucket, s3_region, s3_test_env, s3_uri


class MigrateStorageCommandTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="t-mig", name="Tenant Mig")

    def _seed_local_document(self, storage_dir):
        local = LocalStorage(storage_dir)
        original = local.put_bytes("documents/t/doc/original", b"%PDF fake")
        raw = local.put_bytes("documents/t/doc/ocr/raw_text.json", b'{"raw_text": "x"}')
        doc = Document.objects.create(
            tenant=self.tenant,
            channel="manual",
            file_uri=original.uri,
            raw_text_uri=raw.uri,
        )
        return doc

    def test_apply_migrates_local_to_s3(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ), mock_aws(), s3_test_env():
            create_test_bucket()
            doc = self._seed_local_document(storage_dir)
            assert doc.file_uri.startswith("local://")

            out = StringIO()
            call_command("migrate_storage_local_to_s3", "--apply", stdout=out)

            doc.refresh_from_db()
            assert doc.file_uri == s3_uri("documents/t/doc/original")
            assert doc.raw_text_uri == s3_uri("documents/t/doc/ocr/raw_text.json")

            s3 = boto3.client("s3", region_name=s3_region())
            keys = {o["Key"] for o in s3.list_objects_v2(Bucket=s3_bucket()).get("Contents", [])}
            assert "documents/t/doc/original" in keys
            assert "documents/t/doc/ocr/raw_text.json" in keys
            assert "migrados: 1" in out.getvalue()

    def test_missing_local_file_is_ignored_not_error(self) -> None:
        """Documento com original perdido no disco: ignorado, sem falhar o comando."""
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ), mock_aws(), s3_test_env():
            create_test_bucket()
            doc = Document.objects.create(
                tenant=self.tenant,
                channel="manual",
                file_uri="local://documents/t/ghost/original",  # arquivo nunca gravado
            )
            out = StringIO()
            # não deve levantar CommandError (arquivo ausente não é erro fatal)
            call_command("migrate_storage_local_to_s3", "--apply", stdout=out)

            doc.refresh_from_db()
            assert doc.file_uri == "local://documents/t/ghost/original"  # inalterado
            output = out.getvalue()
            assert "sem arquivo no disco (ignorados): 1" in output
            assert "Migração concluída." in output

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, override_settings(
            DOCUPARSE_LOCAL_STORAGE_DIR=storage_dir
        ), mock_aws(), s3_test_env():
            create_test_bucket()
            doc = self._seed_local_document(storage_dir)

            out = StringIO()
            call_command("migrate_storage_local_to_s3", "--dry-run", stdout=out)

            doc.refresh_from_db()
            assert doc.file_uri.startswith("local://")  # inalterado
            s3 = boto3.client("s3", region_name=s3_region())
            assert s3.list_objects_v2(Bucket=s3_bucket()).get("Contents", []) == []
            assert "DRY-RUN" in out.getvalue()
