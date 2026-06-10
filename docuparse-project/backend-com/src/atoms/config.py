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


class Config(BaseSettings):
    """Configurações do projeto carregadas de variáveis de ambiente.

    Cada campo corresponde a uma env var (case-insensitive).
    Ex: database_url → DATABASE_URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    title: str = "Atoms API"
    description: str = "API for Atoms project"
    version: str = "0.1.0"
    openapi_url: str = "/openapi.json"
    root_path: str = "/"


# Singleton — importar de qualquer lugar do projeto
settings = Config()
