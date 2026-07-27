"""Cobertura de ``exists`` e ``iter_keys`` nos três backends (LocalStorage,
S3Storage via moto e RoutingStorage) — usados pela reconciliação banco ↔ storage.
"""

from __future__ import annotations

import boto3
import pytest
from docuparse_storage import LocalStorage, RoutingStorage, S3Storage
from moto import mock_aws

BUCKET = "docuparse-test"
K1 = "documents/tenant-x/doc-1/original"
K2 = "documents/tenant-x/doc-1/ocr/raw_text.json"
K3 = "outros/coisa"


# -- LocalStorage ----------------------------------------------------------


def test_local_exists_by_key_and_uri(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.put_bytes(K1, b"data")
    assert storage.exists(K1) is True
    assert storage.exists(f"local://{K1}") is True
    assert storage.exists("documents/tenant-x/doc-1/missing") is False


def test_local_iter_keys_with_prefix(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.put_bytes(K1, b"a")
    storage.put_bytes(K2, b"b")
    storage.put_bytes(K3, b"c")
    assert set(storage.iter_keys()) == {K1, K2, K3}
    assert set(storage.iter_keys("documents/")) == {K1, K2}


def test_local_iter_keys_empty_root(tmp_path):
    storage = LocalStorage(tmp_path / "inexistente")
    assert list(storage.iter_keys()) == []


# -- S3Storage (moto) ------------------------------------------------------


@pytest.fixture()
def s3_backend():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield S3Storage(
            bucket=BUCKET, region="us-east-1", access_key="test", secret_key="test"
        )


def test_s3_exists_true_false(s3_backend):
    s3_backend.put_bytes(K1, b"data")
    assert s3_backend.exists(K1) is True
    assert s3_backend.exists(f"s3://{BUCKET}/{K1}") is True
    assert s3_backend.exists("documents/tenant-x/doc-1/missing") is False


def test_s3_iter_keys_with_prefix(s3_backend):
    s3_backend.put_bytes(K1, b"a")
    s3_backend.put_bytes(K2, b"b")
    s3_backend.put_bytes(K3, b"c")
    assert set(s3_backend.iter_keys()) == {K1, K2, K3}
    assert set(s3_backend.iter_keys("documents/")) == {K1, K2}


# -- RoutingStorage --------------------------------------------------------


def test_routing_exists_dispatches_by_scheme(tmp_path):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        s3 = S3Storage(
            bucket=BUCKET, region="us-east-1", access_key="test", secret_key="test"
        )
        local = LocalStorage(tmp_path)
        routing = RoutingStorage(write_scheme="local", local=local, s3=s3)

        local_obj = local.put_bytes(K1, b"local-bytes")
        s3_obj = s3.put_bytes(K2, b"s3-bytes")

        assert routing.exists(local_obj.uri) is True  # local://... → local
        assert routing.exists(s3_obj.uri) is True  # s3://...    → s3
        assert routing.exists("local://documents/x/missing") is False


def test_routing_iter_keys_uses_write_backend(tmp_path):
    local = LocalStorage(tmp_path)
    routing = RoutingStorage(write_scheme="local", local=local)
    local.put_bytes(K1, b"a")
    local.put_bytes(K2, b"b")
    assert set(routing.iter_keys("documents/")) == {K1, K2}
