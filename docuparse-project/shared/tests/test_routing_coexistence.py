"""US3 (T030) — coexistência de referências legadas e dispatch do RoutingStorage.

Uma URI ``local://`` legada continua legível mesmo com o backend de escrita = s3
(migração incremental + rollback). O dispatch escolhe o backend pelo esquema.
"""

from __future__ import annotations

import boto3
import pytest
from docuparse_storage import LocalStorage, RoutingStorage, S3Storage
from moto import mock_aws

KEY = "documents/t/d/original"
LEGACY = "documents/t/d/legacy"


def test_bare_key_uses_write_backend(tmp_path):
    local = LocalStorage(tmp_path)
    routing = RoutingStorage(write_scheme="local", local=local)
    stored = routing.put_bytes(KEY, b"data")
    assert stored.uri == f"local://{KEY}"
    assert routing.get_bytes(KEY) == b"data"  # key nua → backend de escrita (local)


def test_local_scheme_reads_from_local_even_in_s3_write_mode(tmp_path):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        local = LocalStorage(tmp_path)
        s3 = S3Storage(
            bucket="test-bucket", region="us-east-1", access_key="k", secret_key="s"
        )
        # gravamos a referência legada no disco
        local.put_bytes(LEGACY, b"legacy-bytes")
        routing = RoutingStorage(write_scheme="s3", local=local, s3=s3)
        # escrita vai para s3
        assert routing.put_bytes(KEY, b"new").uri.startswith("s3://")
        # leitura da legada local:// continua funcionando
        assert routing.get_bytes(f"local://{LEGACY}") == b"legacy-bytes"
        # leitura da nova s3:// funciona
        assert routing.get_bytes(f"s3://test-bucket/{KEY}") == b"new"


def test_s3_uri_without_backend_raises_clear_error(tmp_path):
    local = LocalStorage(tmp_path)
    routing = RoutingStorage(
        write_scheme="local", local=local, s3=None, s3_provider=None
    )
    with pytest.raises(RuntimeError):
        routing.get_bytes("s3://b/documents/t/d/original")


def test_lazy_s3_provider_built_on_demand(tmp_path):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        local = LocalStorage(tmp_path)
        calls = {"n": 0}

        def provider():
            calls["n"] += 1
            s3 = S3Storage(
                bucket="test-bucket", region="us-east-1", access_key="k", secret_key="s"
            )
            s3.put_bytes("documents/t/d/original", b"lazy")
            return s3

        routing = RoutingStorage(
            write_scheme="local", local=local, s3=None, s3_provider=provider
        )
        # provider só é chamado quando surge uma URI s3://
        assert calls["n"] == 0
        assert routing.get_bytes("s3://test-bucket/documents/t/d/original") == b"lazy"
        assert calls["n"] == 1


def test_invalid_write_scheme_rejected(tmp_path):
    with pytest.raises(ValueError):
        RoutingStorage(write_scheme="gcs", local=LocalStorage(tmp_path))
