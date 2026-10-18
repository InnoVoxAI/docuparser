"""Tokens do Superlógica por tenant, cifrados com a chave `DOCUPARSE_SECRETS_KEY`.

Os tokens só existem em claro dentro de `load_superlogica_tokens`, no momento de
montar a fonte. Nada daqui devolve ou registra o valor.
"""

from __future__ import annotations

import os
from typing import NamedTuple

from cryptography.fernet import Fernet, InvalidToken
from documents.models import SETTINGS_SINGLETON_ID, IntegrationSettings

KEY_ENV = "DOCUPARSE_SECRETS_KEY"


class CredentialsError(Exception):
    """Credenciais ausentes, ilegíveis ou sem chave de criptografia. A mensagem é legível."""


class SuperlogicaTokens(NamedTuple):
    app_token: str
    access_token: str


def _fernet() -> Fernet:
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise CredentialsError(
            f"A chave de criptografia ({KEY_ENV}) não está configurada."
        )
    try:
        return Fernet(key)
    except ValueError:
        raise CredentialsError(
            f"A chave de criptografia ({KEY_ENV}) é inválida."
        ) from None


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise CredentialsError(
            "Não foi possível ler as credenciais salvas. Informe os tokens novamente."
        ) from None


def credentials_configured(config: IntegrationSettings | None) -> bool:
    return bool(
        config
        and config.superlogica_app_token_enc
        and config.superlogica_access_token_enc
    )


def save_superlogica_tokens(
    config: IntegrationSettings, app_token: str, access_token: str
) -> None:
    config.superlogica_app_token_enc = _encrypt(app_token)
    config.superlogica_access_token_enc = _encrypt(access_token)


def load_superlogica_tokens() -> SuperlogicaTokens:
    config = IntegrationSettings.objects.filter(id=SETTINGS_SINGLETON_ID).first()
    if not credentials_configured(config):
        raise CredentialsError("As credenciais do Superlógica não foram configuradas.")
    return SuperlogicaTokens(
        _decrypt(config.superlogica_app_token_enc),
        _decrypt(config.superlogica_access_token_enc),
    )
