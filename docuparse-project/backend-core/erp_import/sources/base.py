"""Fonte de cadastro externo (condomínios e planos de contas).

O restante do sistema só enxerga estes objetos, nunca o payload bruto da fonte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SourceError(Exception):
    """Falha ao ler a fonte. A mensagem é legível e nunca carrega o corpo da resposta."""


class SourceAuthError(SourceError):
    """A fonte recusou as credenciais."""


@dataclass(frozen=True)
class SourceCondominium:
    external_id: str
    name: str
    # Vazio quando ausente ou com dígitos verificadores inválidos (`cnpj_invalid`).
    cnpj: str
    cnpj_invalid: bool
    is_active: bool
    chart_external_id: str
    address: str
    zip_code: str
    city: str


@dataclass(frozen=True)
class SourceChart:
    external_id: str
    name: str


@dataclass(frozen=True)
class SourceAccount:
    code: str
    name: str
    # Vazio nas contas de primeiro nível.
    parent_code: str
    # O pai deduzido do código não existe no plano.
    orphan: bool


class RegistrySource(Protocol):
    source_name: str

    def list_condominiums(self) -> list[SourceCondominium]: ...

    def list_charts(self) -> list[SourceChart]: ...

    def list_accounts(self, chart_external_id: str) -> list[SourceAccount]: ...
