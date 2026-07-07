"""US4 (T027) — falhas de storage explícitas e distinguíveis.

Objeto inexistente → FileNotFoundError; falha de conexão/credencial → exceção
propagada distinta (nunca mascarada como "não encontrado").
"""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from docuparse_storage import S3Storage

URI = "s3://b/documents/t/d/original"


class _RaisingClient:
    """Client stub que sempre levanta a exceção fornecida (sem rede)."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def get_object(self, **_kwargs):
        raise self._exc


def _client_error(code: str, http_status: int) -> ClientError:
    return ClientError(
        {"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": http_status}},
        "GetObject",
    )


def _storage_with_client(exc: Exception) -> S3Storage:
    # Construir o S3Storage cria um client boto3 offline; substituímos por um stub.
    storage = S3Storage(bucket="b", region="us-east-1", access_key="k", secret_key="s")
    storage._client = _RaisingClient(exc)  # type: ignore[assignment]
    return storage


@pytest.mark.parametrize("code,http", [("NoSuchKey", 404), ("404", 404), ("NoSuchBucket", 404)])
def test_not_found_maps_to_filenotfound(code, http):
    storage = _storage_with_client(_client_error(code, http))
    with pytest.raises(FileNotFoundError):
        storage.get_bytes(URI)


def test_access_denied_propagates_as_clienterror_not_filenotfound():
    storage = _storage_with_client(_client_error("AccessDenied", 403))
    with pytest.raises(ClientError):
        storage.get_bytes(URI)
    # e explicitamente não é FileNotFoundError
    with pytest.raises(ClientError):
        try:
            storage.get_bytes(URI)
        except FileNotFoundError:  # pragma: no cover
            pytest.fail("AccessDenied não deve virar FileNotFoundError")


def test_connection_error_propagates():
    storage = _storage_with_client(EndpointConnectionError(endpoint_url="http://minio:9000"))
    with pytest.raises(EndpointConnectionError):
        storage.get_bytes(URI)
