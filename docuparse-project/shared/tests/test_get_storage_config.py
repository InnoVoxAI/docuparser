"""US2 (T022) — seleção do backend por ambiente, sem regressão.

Default = local (comportamento histórico); s3 ativado por env; falha explícita
quando s3 sem bucket; boto3 não é exigido no modo local.
"""

from __future__ import annotations

import os
from unittest import mock

import boto3
import pytest
from docuparse_storage import RoutingStorage, get_storage
from moto import mock_aws

KEY = "documents/t/d/original"


def _clean_env(**overrides):
    base = {
        "DOCUPARSE_STORAGE_BACKEND": "",
        "DOCUPARSE_LOCAL_STORAGE_DIR": "",
        "S3_BUCKET": "",
        "S3_ENDPOINT_URL": "",
        "S3_REGION": "",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
    }
    base.update(overrides)
    return mock.patch.dict(os.environ, base, clear=False)


def test_default_is_local_and_writes_local_uri(tmp_path):
    with _clean_env(DOCUPARSE_LOCAL_STORAGE_DIR=str(tmp_path)):
        storage = get_storage()
        assert isinstance(storage, RoutingStorage)
        stored = storage.put_bytes(KEY, b"data")
        assert stored.uri == f"local://{KEY}"
        assert storage.get_bytes(stored.uri) == b"data"


def test_local_dir_resolved_from_env(tmp_path):
    # A raiz local vem exclusivamente do ambiente; cada serviço exporta seu
    # default histórico via DOCUPARSE_LOCAL_STORAGE_DIR (evita regressão de caminho).
    with _clean_env(DOCUPARSE_LOCAL_STORAGE_DIR=str(tmp_path)):
        storage = get_storage()
        stored = storage.put_bytes(KEY, b"data")
        assert (tmp_path / KEY).read_bytes() == b"data"
        assert stored.uri == f"local://{KEY}"


def test_s3_backend_writes_s3_uri():
    with (
        mock_aws(),
        _clean_env(
            DOCUPARSE_STORAGE_BACKEND="s3",
            S3_BUCKET="docuparse",
            S3_REGION="us-east-1",
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
        ),
    ):
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="docuparse")
        storage = get_storage()
        stored = storage.put_bytes(KEY, b"data")
        assert stored.uri == f"s3://docuparse/{KEY}"


def test_s3_without_bucket_fails_explicitly_no_silent_fallback():
    with _clean_env(DOCUPARSE_STORAGE_BACKEND="s3"):
        with pytest.raises(RuntimeError):
            get_storage()


def test_invalid_backend_raises():
    with _clean_env(DOCUPARSE_STORAGE_BACKEND="gcs"):
        with pytest.raises(RuntimeError):
            get_storage()
