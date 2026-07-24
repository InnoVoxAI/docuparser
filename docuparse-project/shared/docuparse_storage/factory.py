from __future__ import annotations

import logging
import os

from .local import LocalStorage
from .routing import RoutingStorage
from .s3 import S3Storage

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_STORAGE_DIR = "/data/storage"


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return value.strip() if value is not None else default


def _build_s3_from_env() -> S3Storage:
    """Constrói o ``S3Storage`` a partir do ambiente, falhando de forma explícita
    quando a configuração está incompleta (nunca cai silenciosamente em local)."""
    bucket = _env("S3_BUCKET")
    if not bucket:
        raise RuntimeError(
            "DOCUPARSE_STORAGE_BACKEND=s3 requer S3_BUCKET configurado (via env/secret)."
        )
    return S3Storage(
        bucket=bucket,
        endpoint_url=_env("S3_ENDPOINT_URL") or None,
        region=_env("S3_REGION") or None,
        access_key=_env("AWS_ACCESS_KEY_ID") or None,
        secret_key=_env("AWS_SECRET_ACCESS_KEY") or None,
    )


def get_storage() -> RoutingStorage:
    """Único ponto de instanciação de storage no código de aplicação.

    Seleciona o backend por ``DOCUPARSE_STORAGE_BACKEND`` (default ``local``) e
    devolve um ``RoutingStorage`` que escreve no backend configurado e lê
    despachando pelo esquema da URI. No default, o comportamento é idêntico ao
    histórico (LocalStorage), e ``boto3`` não é importado.

    Toda a configuração vem do ambiente (assim como bucket, endpoint e
    credenciais do S3): o diretório local é resolvido de
    ``DOCUPARSE_LOCAL_STORAGE_DIR`` (com fallback de container). Cada serviço
    define seu default histórico exportando essa variável na sua camada de
    config, de modo que os chamadores nunca precisam passar o caminho.
    """
    backend = _env("DOCUPARSE_STORAGE_BACKEND", "local").lower() or "local"
    if backend not in {"local", "s3"}:
        raise RuntimeError(
            f"DOCUPARSE_STORAGE_BACKEND inválido: {backend!r} (use 'local' ou 's3')."
        )

    if backend == "s3":
        # Falha explícita já na construção se a config estiver incompleta.
        s3 = _build_s3_from_env()
        local = LocalStorage(
            _env("DOCUPARSE_LOCAL_STORAGE_DIR", DEFAULT_LOCAL_STORAGE_DIR)
        )
        logger.info("storage.backend_selected", extra={"backend": "s3"})
        return RoutingStorage(
            write_scheme="s3", local=local, s3=s3, s3_provider=_build_s3_from_env
        )

    local = LocalStorage(_env("DOCUPARSE_LOCAL_STORAGE_DIR", DEFAULT_LOCAL_STORAGE_DIR))
    logger.info("storage.backend_selected", extra={"backend": "local"})
    # Modo local: S3 é construído sob demanda (lazy) apenas se surgir uma URI s3://
    # legada para leitura — assim o modo local não exige boto3.
    return RoutingStorage(
        write_scheme="local", local=local, s3=None, s3_provider=_build_s3_from_env
    )
