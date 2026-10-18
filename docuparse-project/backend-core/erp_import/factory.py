from __future__ import annotations

from documents.models import SETTINGS_SINGLETON_ID, IntegrationSettings

from erp_import.credentials import load_superlogica_tokens
from erp_import.sources.superlogica import (
    DEFAULT_BASE_URL,
    SuperlogicaClient,
    SuperlogicaSource,
)


def build_superlogica_source() -> SuperlogicaSource:
    """Fonte do tenant atual. Levanta `CredentialsError` se não houver credenciais."""
    tokens = load_superlogica_tokens()
    config = IntegrationSettings.objects.filter(id=SETTINGS_SINGLETON_ID).first()
    base_url = (config.superlogica_base_url if config else "") or DEFAULT_BASE_URL
    return SuperlogicaSource(
        SuperlogicaClient(tokens.app_token, tokens.access_token, base_url)
    )


def administrator_cnpj() -> str:
    config = IntegrationSettings.objects.filter(id=SETTINGS_SINGLETON_ID).first()
    return config.administrator_cnpj if config else ""
