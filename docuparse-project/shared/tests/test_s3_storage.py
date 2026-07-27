"""US1 (T009) — testes de S3Storage contra moto (mock S3, sem rede/disco)."""

from __future__ import annotations

import hashlib

import boto3
import pytest
from docuparse_storage import S3Storage, StoredObject
from moto import mock_aws

BUCKET = "docuparse-test"
KEY = "documents/tenant-x/doc-1/original"


@pytest.fixture()
def s3_backend():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield S3Storage(
            bucket=BUCKET, region="us-east-1", access_key="test", secret_key="test"
        )


def test_put_returns_stored_object_with_s3_uri_and_hash(s3_backend):
    content = b"%PDF-1.7 fake"
    stored = s3_backend.put_bytes(KEY, content)
    assert isinstance(stored, StoredObject)
    assert stored.uri == f"s3://{BUCKET}/{KEY}"
    assert stored.key == KEY
    assert stored.size_bytes == len(content)
    assert stored.sha256 == hashlib.sha256(content).hexdigest()


def test_roundtrip_by_uri_and_by_bare_key(s3_backend):
    stored = s3_backend.put_bytes(KEY, b"payload")
    assert s3_backend.get_bytes(stored.uri) == b"payload"
    assert s3_backend.get_bytes(KEY) == b"payload"  # key nua resolve no bucket default


def test_delete_is_idempotent(s3_backend):
    s3_backend.put_bytes(KEY, b"x")
    s3_backend.delete(f"s3://{BUCKET}/{KEY}")
    # deletar de novo (inexistente) não deve levantar
    s3_backend.delete(f"s3://{BUCKET}/{KEY}")
    with pytest.raises(FileNotFoundError):
        s3_backend.get_bytes(f"s3://{BUCKET}/{KEY}")


def test_large_document_20mb_roundtrip(s3_backend):
    # SC-004 / FR-010: 20 MB grava e lê sem erro.
    content = b"a" * (20 * 1024 * 1024)
    stored = s3_backend.put_bytes(KEY, content)
    assert stored.size_bytes == 20 * 1024 * 1024
    assert s3_backend.get_bytes(stored.uri) == content


@pytest.mark.parametrize("bad_key", ["/abs/key", "documents/../escape", "  "])
def test_invalid_keys_rejected(s3_backend, bad_key):
    with pytest.raises(ValueError):
        s3_backend.put_bytes(bad_key, b"x")


def test_empty_bucket_rejected():
    with pytest.raises(ValueError):
        S3Storage(bucket="")
