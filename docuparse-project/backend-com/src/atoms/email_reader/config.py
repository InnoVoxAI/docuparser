"""
config.py
---------
Configuração do EmailReader via variáveis de ambiente ou instanciação direta.

Variáveis de ambiente suportadas:
    IMAP_HOST       ex: imap.gmail.com
    IMAP_PORT       ex: 993
    IMAP_USERNAME   ex: seuemail@gmail.com
    IMAP_PASSWORD   ex: sua_app_password
    IMAP_SSL        ex: true
    IMAP_FOLDER     ex: INBOX
"""
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

# Preset de hosts comuns para referência rápida
KNOWN_HOSTS = {
    "gmail": "imap.gmail.com",
    "outlook": "outlook.office365.com",
    "yahoo": "imap.mail.yahoo.com",
    "zoho": "imap.zoho.com",
}


class IMAPConfig(BaseSettings):
    """Configurações do projeto carregadas de variáveis de ambiente.

    Cada campo corresponde a uma env var (case-insensitive).
    Ex: database_url → DATABASE_URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="imap_reader_",
    )

    # Configurações de conexão IMAP quando rodando como daemon
    run_as_daemon: bool = (
        False  # Se True, inicia a tarefa de busca periódica no startup do FastAPI
    )
    host: str = "imap.gmail.com"
    username: str = ""
    password: SecretStr = SecretStr("")
    port: int = 993
    ssl: bool = True
    folder: str = "INBOX"
    limit: int = 10
    mark_as_read: bool = False

    webhook_url: str = ""  # URL do webhook para enviar os attachments processados
    headers: dict = {}
    daemon_interval: int = (
        600  # Intervalo em segundos entre buscas periódicas - default 10 minutos
    )


imap_config = IMAPConfig()
