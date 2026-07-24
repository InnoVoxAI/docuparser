"""Config de S3/MinIO para os testes — puxada de ``settings``/``os.environ``,
nunca hardcoded no código dos testes.

Objetivo: não deixar valores (nem credenciais de teste) escritos no código. Em
execução dentro do container, tudo vem do ambiente/.env (o mesmo que o código de
produção lê via ``docuparse_storage.factory`` / ``_build_s3_from_env``). Fora do
container (CI/local sem .env), caímos em andaimes **não-sensíveis** (nome de
bucket e região) e o ``moto`` provê credenciais fictícias — por isso as chaves
``AWS_*`` nunca precisam ser escritas aqui.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from unittest import mock

import boto3
from django.conf import settings


def s3_bucket() -> str:
    """Bucket dos testes: de ``settings.S3_BUCKET`` (lido do env) ou andaime."""
    return settings.S3_BUCKET or "test-bucket"


def s3_region() -> str:
    return settings.S3_REGION or "us-east-1"


def s3_uri(key: str) -> str:
    """Monta a URI ``s3://<bucket>/<key>`` usando o bucket efetivo (para asserts)."""
    return f"s3://{s3_bucket()}/{key}"


def create_test_bucket() -> None:
    """Cria o bucket no S3 mockado (chamar dentro de ``mock_aws``)."""
    boto3.client("s3", region_name=s3_region()).create_bucket(Bucket=s3_bucket())


@contextmanager
def s3_test_env():
    """Publica no ``os.environ`` a config de S3 que o código de produção lê,
    derivando de ``settings``/``os.environ`` — sem literais de credencial.

    As chaves ``AWS_*`` só são repassadas se já estiverem no ambiente (container);
    na ausência, o ``moto`` opera com credenciais próprias.

    ``S3_ENDPOINT_URL`` é **forçado a vazio** dentro do contexto: os testes usam o
    S3 mockado (``moto``), então nunca devem apontar para um MinIO/S3 real — do
    contrário poluiriam a infra e/ou o ``moto`` deixaria de interceptar.
    """
    env = {
        "DOCUPARSE_STORAGE_BACKEND": "s3",
        "S3_BUCKET": s3_bucket(),
        "S3_REGION": s3_region(),
        "S3_ENDPOINT_URL": "",  # usa o endpoint AWS default → interceptado pelo moto
    }
    for cred in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        value = os.environ.get(cred)
        if value:
            env[cred] = value
    with mock.patch.dict(os.environ, env):
        yield
