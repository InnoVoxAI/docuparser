from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

from .keys import StoredObject

if TYPE_CHECKING:  # pragma: no cover - somente para type-checking
    from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)

_NOT_FOUND_CODES = {"NoSuchKey", "NoSuchBucket", "404", "NotFound"}


class S3Storage:
    """Storage de objetos S3/MinIO com o mesmo contrato de ``LocalStorage``.

    ``boto3`` é importado de forma lazy (dentro do ``__init__``) para que serviços
    em modo ``local`` não precisem da dependência em runtime.
    """

    scheme = "s3"

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 30.0,
        max_attempts: int = 3,
    ) -> None:
        if not bucket:
            raise ValueError("S3Storage requires a non-empty bucket")

        import boto3  # lazy import — evita exigir boto3 no modo local
        from botocore.config import Config

        self._bucket = bucket
        client_kwargs: dict[str, object] = {
            "config": Config(
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={"max_attempts": max_attempts, "mode": "standard"},
            ),
        }
        if region:
            client_kwargs["region_name"] = region
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        self._client: S3Client = boto3.client("s3", **client_kwargs)

    # -- API pública -------------------------------------------------------

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        self._validate_key(key)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        logger.debug(
            "s3.uploaded",
            extra={"bucket": self._bucket, "key": key, "size": len(content)},
        )
        return StoredObject(
            uri=f"{self.scheme}://{self._bucket}/{key}",
            key=key,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def get_bytes(self, uri_or_key: str) -> bytes:
        bucket, key = self._resolve(uri_or_key)
        from botocore.exceptions import ClientError

        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:  # 404/NoSuchKey → FileNotFoundError; resto propaga
            if self._is_not_found(exc):
                raise FileNotFoundError(f"s3://{bucket}/{key}") from exc
            raise

    def delete(self, uri_or_key: str) -> None:
        bucket, key = self._resolve(uri_or_key)
        # delete_object é idempotente no S3 (não falha se a key não existir).
        self._client.delete_object(Bucket=bucket, Key=key)

    def exists(self, uri_or_key: str) -> bool:
        bucket, key = self._resolve(uri_or_key)
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:  # 404/NoSuchKey → False; conexão/credencial propaga
            if self._is_not_found(exc):
                return False
            raise

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"]

    # -- Helpers -----------------------------------------------------------

    def _resolve(self, uri_or_key: str) -> tuple[str, str]:
        """Devolve (bucket, key) a partir de ``s3://bucket/key`` ou key nua."""
        if uri_or_key.startswith(f"{self.scheme}://"):
            rest = uri_or_key[len(self.scheme) + 3 :]
            bucket, _, key = rest.partition("/")
            if not bucket or not key:
                raise ValueError(f"Invalid s3 URI: {uri_or_key!r}")
            self._validate_key(key)
            return bucket, key
        self._validate_key(uri_or_key)
        return self._bucket, uri_or_key

    @staticmethod
    def _is_not_found(exc: object) -> bool:
        response = getattr(exc, "response", None) or {}
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        code = str(error.get("Code", ""))
        status = (
            str(response.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))
            if isinstance(response, dict)
            else ""
        )
        return code in _NOT_FOUND_CODES or status == "404"

    @staticmethod
    def _validate_key(key: str) -> None:
        # Mesma proteção de path traversal do LocalStorage (chaves são idênticas
        # entre backends), para manter o contrato uniforme.
        from pathlib import PurePosixPath

        path = PurePosixPath(key)
        if path.is_absolute() or ".." in path.parts or not key.strip():
            raise ValueError(f"Invalid storage key: {key!r}")
