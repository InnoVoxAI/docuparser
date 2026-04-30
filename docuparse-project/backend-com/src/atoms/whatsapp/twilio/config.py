"""Configuração centralizada via variáveis de ambiente.

Usa pydantic-settings para carregar, validar e tipar todas as configurações
do projeto a partir de variáveis de ambiente ou arquivo .env.

Uso:
    from whatsapp_langchain.shared.config import settings

    print(twilio_settings.database_url)
    print(twilio_settings.rate_limit_per_hour)

A maior parte das configurações tem defaults sensatos para desenvolvimento local.
Segredos compartilhados do painel/admin devem ser preenchidos explicitamente.
"""
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

MIN_PRODUCTION_SECRET_LENGTH = 32


class TwilioConfig(BaseSettings):
    """Configurações do projeto carregadas de variáveis de ambiente.

    Cada campo corresponde a uma env var (case-insensitive).
    Ex: database_url → DATABASE_URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="twilio_",
    )
    # --- Twilio ---
    # Inbound (validação de assinatura no webhook)
    validate_twilio_signature: bool = False
    twilio_auth_token: str = ""
    twilio_webhook_url: str = ""

    # --- Rate Limit ---
    rate_limit_per_hour: int = 30

    # --- Internal Service Token ---
    # Token compartilhado entre frontend e API para proteger rotas administrativas.
    # Preencha também em desenvolvimento; em produção, use um token forte.
    internal_service_token: str = ""

    # --- Webhook configuration ---
    webhook_url: str = "http://localhost:8080/engine-rest/inbound/webhook"
    headers: dict = {}


# Singleton — importar de qualquer lugar do projeto
twilio_settings = TwilioConfig()
