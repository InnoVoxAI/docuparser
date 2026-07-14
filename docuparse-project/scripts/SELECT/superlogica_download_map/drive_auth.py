"""Autenticação OAuth 2.0 ("Desktop app") no Google Drive, somente leitura.

Fluxo (Seção 1.1):
- reutiliza ``token.json`` se válido;
- se expirado, tenta ``refresh``; se o refresh falhar, apaga o token e refaz o
  login interativo;
- se não houver token, executa o login no navegador (cria ``token.json``).

Falha de autenticação irrecuperável → :class:`AuthError` (E-01, fatal).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # evita importar as libs pesadas fora de execução real
    from google.oauth2.credentials import Credentials

    from .config import Config


class AuthError(RuntimeError):
    """Falha fatal de autenticação (E-01). A CLI aborta com instrução de re-login."""


def _save_token(creds: Credentials, config: Config) -> None:
    config.token_file.write_text(creds.to_json(), encoding="utf-8")


def get_credentials(config: Config) -> Credentials:
    """Obtém credenciais válidas do Drive, reaproveitando/renovando o token."""
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    scopes = list(config.drive_scopes)
    creds: Credentials | None = None

    if config.token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(config.token_file), scopes)
        except (ValueError, KeyError):
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, config)
            return creds
        except GoogleAuthError:
            # Refresh falhou → descartar token e cair no login interativo.
            _delete_token(config)
            creds = None

    return _interactive_login(config, scopes)


def _delete_token(config: Config) -> None:
    try:
        config.token_file.unlink()
    except OSError:
        pass


def _interactive_login(config: Config, scopes: list[str]) -> Credentials:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not config.credentials_file.exists():
        raise AuthError(
            f"credentials.json não encontrado em '{config.credentials_file}'. "
            "Coloque a credencial OAuth 'Desktop app' no diretório de trabalho "
            "(ou use --credentials)."
        )
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(config.credentials_file), scopes)
        creds = flow.run_local_server(port=0)
    except Exception as exc:  # noqa: BLE001 — qualquer falha aqui é fatal (E-01)
        raise AuthError(
            "Falha no login OAuth do Drive. Apague o token.json e tente novamente "
            f"({exc})."
        ) from exc
    _save_token(creds, config)
    return creds


def build_drive_service(creds: Credentials):
    """Cria o cliente da Drive API v3."""
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=creds, cache_discovery=False)
