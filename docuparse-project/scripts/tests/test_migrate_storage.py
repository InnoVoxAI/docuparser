"""US3 (T031) — testes do script de migração local:// → s3:// (idempotente,
retomável, sem depender de Django)."""

from __future__ import annotations

import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/ no path

from migrate_storage_local_to_s3 import migrate_documents, migrate_uri  # noqa: E402

from docuparse_storage import LocalStorage, S3Storage  # noqa: E402

BUCKET = "docuparse-mig"


class FakeDoc:
    def __init__(self, doc_id, file_uri="", raw_text_uri=""):
        self.id = doc_id
        self.file_uri = file_uri
        self.raw_text_uri = raw_text_uri
        self.saved_fields = None

    def save(self, update_fields=None):
        self.saved_fields = list(update_fields or [])


@pytest.fixture()
def backends(tmp_path):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        local = LocalStorage(tmp_path)
        s3 = S3Storage(bucket=BUCKET, region="us-east-1", access_key="k", secret_key="s")
        yield local, s3


def test_migrate_uri_copies_and_returns_s3(backends):
    local, s3 = backends
    local.put_bytes("documents/t/d/original", b"bytes")
    new = migrate_uri("local://documents/t/d/original", local, s3, dry_run=False)
    assert new == f"s3://{BUCKET}/documents/t/d/original"
    assert s3.get_bytes(new) == b"bytes"


def test_migrate_uri_is_idempotent(backends):
    local, s3 = backends
    # já em s3:// ou vazio → inalterado
    assert migrate_uri("s3://x/documents/t/d/original", local, s3, dry_run=False) == "s3://x/documents/t/d/original"
    assert migrate_uri("", local, s3, dry_run=False) == ""


def test_dry_run_does_not_write_or_save(backends):
    local, s3 = backends
    local.put_bytes("documents/t/d/original", b"bytes")
    doc = FakeDoc("d1", file_uri="local://documents/t/d/original")
    stats = migrate_documents([doc], local, s3, dry_run=True)
    assert stats.migrated == 1
    assert doc.saved_fields is None  # nada salvo
    # objeto não foi realmente gravado no s3
    with pytest.raises(FileNotFoundError):
        s3.get_bytes(f"s3://{BUCKET}/documents/t/d/original")


def test_apply_migrates_both_fields_and_updates_db(backends):
    local, s3 = backends
    local.put_bytes("documents/t/d/original", b"orig")
    local.put_bytes("documents/t/d/ocr/raw_text.json", b"{}")
    doc = FakeDoc(
        "d1",
        file_uri="local://documents/t/d/original",
        raw_text_uri="local://documents/t/d/ocr/raw_text.json",
    )
    stats = migrate_documents([doc], local, s3, dry_run=False)
    assert stats.migrated == 1 and stats.scanned == 1
    assert doc.file_uri == f"s3://{BUCKET}/documents/t/d/original"
    assert doc.raw_text_uri == f"s3://{BUCKET}/documents/t/d/ocr/raw_text.json"
    assert set(doc.saved_fields) == {"file_uri", "raw_text_uri"}


def test_already_migrated_doc_is_skipped(backends):
    local, s3 = backends
    doc = FakeDoc("d1", file_uri=f"s3://{BUCKET}/documents/t/d/original")
    stats = migrate_documents([doc], local, s3, dry_run=False)
    assert stats.skipped == 1 and stats.migrated == 0
    assert doc.saved_fields is None


def test_missing_local_object_recorded_as_missing_not_error(backends):
    local, s3 = backends
    doc = FakeDoc("d1", file_uri="local://documents/t/d/gone")
    stats = migrate_documents([doc], local, s3, dry_run=False)
    # Arquivo ausente vira "missing" (ignorado), NÃO erro — não trava a migração.
    assert stats.missing and "d1:file_uri" in stats.missing[0]
    assert stats.errors == []
    assert stats.skipped == 1 and stats.migrated == 0
    assert doc.file_uri == "local://documents/t/d/gone"  # inalterado (não perde acesso)
