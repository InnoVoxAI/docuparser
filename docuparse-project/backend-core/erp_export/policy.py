"""Política de segurança da escrita no Superlógica.

Os tokens do tenant são de um ambiente real. Por isso a política é a primeira coisa
que o conector consulta, e todo padrão aqui é o mais seguro:

- `disabled` e `mock` nunca abrem conexão com o ERP.
- `dry_run` (ligado por padrão) monta e valida o payload e não envia.
- `sandbox` só envia para um host listado em `SUPERLOGICA_SANDBOX_HOSTS` (vazio por
  padrão) e nunca para o host de produção.
- `live` exige as quatro condições juntas: habilitação do tenant, a variável
  `SUPERLOGICA_LIVE_WRITES=1`, o contrato de escrita verificado no spike
  (`payload.CONTRACT_VERIFIED`) e o host de produção.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from documents.models import IntegrationSettings

from erp_export import payload

PRODUCTION_HOST = "api.superlogica.net"
SANDBOX_HOSTS_ENV = "SUPERLOGICA_SANDBOX_HOSTS"
LIVE_WRITES_ENV = "SUPERLOGICA_LIVE_WRITES"
DEFAULT_PRODUCTION_URL = f"https://{PRODUCTION_HOST}/v2/condor"

Mode = IntegrationSettings.SuperlogicaMode


@dataclass(frozen=True)
class WritePolicy:
    mode: str
    dry_run: bool
    # Só há envio quando nenhuma trava recusa e o dry-run está desligado.
    send_allowed: bool
    # Motivo da recusa quando o modo exige envio e uma trava o impede.
    blocked_reason: str
    base_url: str


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _sandbox_hosts(environ: Mapping[str, str]) -> set[str]:
    raw = environ.get(SANDBOX_HOSTS_ENV, "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _blocked_reason(
    config: IntegrationSettings, environ: Mapping[str, str], contract_verified: bool
) -> tuple[str, str]:
    """(motivo, URL base) — motivo vazio quando as travas permitem enviar."""
    base_url = (config.superlogica_base_url or "").strip()
    if config.superlogica_mode == Mode.SANDBOX:
        if not base_url:
            return "Informe a URL do ambiente de teste do Superlógica.", base_url
        host = _host(base_url)
        if host == PRODUCTION_HOST:
            return (
                "O modo teste não pode apontar para o ambiente de produção do Superlógica.",
                base_url,
            )
        if host not in _sandbox_hosts(environ):
            return (
                f"O host do ambiente de teste não está autorizado ({SANDBOX_HOSTS_ENV}).",
                base_url,
            )
        return "", base_url

    # live
    base_url = base_url or DEFAULT_PRODUCTION_URL
    if not getattr(config, "superlogica_live_enabled", False):
        return "O envio real não está habilitado para este cliente.", base_url
    if environ.get(LIVE_WRITES_ENV, "") != "1":
        return f"O envio real está desligado no servidor ({LIVE_WRITES_ENV}).", base_url
    if not contract_verified:
        return (
            "O contrato de escrita do Superlógica ainda não foi verificado em ambiente de teste.",
            base_url,
        )
    if _host(base_url) != PRODUCTION_HOST:
        return "O envio real só vai para o host de produção do Superlógica.", base_url
    return "", base_url


def evaluate_policy(
    config: IntegrationSettings,
    *,
    environ: Mapping[str, str] | None = None,
    contract_verified: bool | None = None,
) -> WritePolicy:
    environ = os.environ if environ is None else environ
    verified = (
        payload.CONTRACT_VERIFIED if contract_verified is None else contract_verified
    )
    mode = config.superlogica_mode

    if mode not in (Mode.SANDBOX, Mode.LIVE):
        # disabled e mock: nunca enviam ao Superlógica.
        return WritePolicy(mode, False, False, "", "")

    dry_run = bool(getattr(config, "superlogica_dry_run", True))
    reason, base_url = _blocked_reason(config, environ, verified)
    return WritePolicy(
        mode=mode,
        dry_run=dry_run,
        send_allowed=not dry_run and not reason,
        blocked_reason=reason,
        base_url=base_url,
    )


def confirmation_required(config: IntegrationSettings) -> bool:
    """Em sandbox e live o analista confirma antes do primeiro envio."""
    return config.superlogica_mode in (Mode.SANDBOX, Mode.LIVE)
