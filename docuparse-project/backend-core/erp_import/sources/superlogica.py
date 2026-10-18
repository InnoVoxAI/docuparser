"""Fonte do Superlógica Condomínios. Somente leitura (GET).

Comportamento da API conforme `memories/reference/Superlógica API Condomínios - fatos
verificados`. Cada campo é lido por nome: o que não está listado aqui (inclusive
`st_token_emp`) nunca sai deste módulo.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests
from condominiums.tax_ids import is_valid_cnpj, normalize_tax_id
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from erp_import.sources.base import (
    SourceAccount,
    SourceAuthError,
    SourceChart,
    SourceCondominium,
    SourceError,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.superlogica.net/v2/condor"
PAGE_SIZE = 50
MAX_PAGES = 200
# Nome do plano: campo ainda não verificado na API, cai para o id.
_CHART_NAME_FIELDS = ("st_descricao_plc", "st_nome_plc")


class ReadOnlyViolation(RuntimeError):
    """Tentativa de usar o cliente com um método que não seja GET."""


class SuperlogicaClient:
    """Cliente HTTP que só faz GET, com timeout, retentativa e espera entre chamadas."""

    def __init__(
        self,
        app_token: str,
        access_token: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        session: requests.Session | None = None,
        timeout: float = 15,
        pause: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._pause = pause
        self._sleep = sleep
        self._calls = 0
        self._session = session or self._build_session()
        self._session.headers.update(
            {
                "app_token": app_token,
                "access_token": access_token,
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _build_session() -> requests.Session:
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def get(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        return self._send("GET", path, params)

    def _send(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> list[Any]:
        if method.upper() != "GET":
            raise ReadOnlyViolation(
                f"O cliente do Superlógica é somente leitura ({method})."
            )
        if self._calls:
            self._sleep(self._pause)
        self._calls += 1

        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            response = self._session.request(
                "GET", url, params=params, timeout=self._timeout
            )
        except requests.RequestException as exc:
            # Só o tipo do erro: a mensagem da biblioteca pode ecoar a requisição.
            raise SourceError(
                f"Falha de rede ao consultar o Superlógica em {path} ({type(exc).__name__})."
            ) from None

        logger.debug("superlogica_get path=%s status=%s", path, response.status_code)
        if response.status_code in (401, 403):
            raise SourceAuthError(
                f"O Superlógica recusou as credenciais (HTTP {response.status_code})."
            )
        if not response.ok:
            raise SourceError(
                f"O Superlógica respondeu HTTP {response.status_code} em {path}."
            )
        try:
            payload = response.json()
        except ValueError:
            raise SourceError(
                f"O Superlógica devolveu uma resposta que não é JSON em {path}."
            ) from None
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            payload = payload["data"]
        if not isinstance(payload, list) or not all(
            isinstance(row, dict) for row in payload
        ):
            raise SourceError(
                f"O Superlógica devolveu um formato inesperado em {path}."
            )
        return payload


def _text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    return "" if value is None else str(value).strip()


def _normalize_condominium(row: dict[str, Any]) -> SourceCondominium:
    external_id = _text(row, "id_condominio_cond")
    if not external_id:
        raise SourceError("O Superlógica devolveu um condomínio sem id.")
    # O CNPJ vem em `st_cpf_cond`; `st_cnpj_cond` é a alternativa.
    raw_cnpj = _text(row, "st_cpf_cond") or _text(row, "st_cnpj_cond")
    cnpj = normalize_tax_id(raw_cnpj)
    valid = bool(cnpj) and is_valid_cnpj(cnpj)
    return SourceCondominium(
        external_id=external_id,
        name=_text(row, "st_nome_cond"),
        cnpj=cnpj if valid else "",
        cnpj_invalid=bool(cnpj) and not valid,
        is_active=_text(row, "fl_ativo_cond") == "1",
        chart_external_id=_text(row, "id_planoconta_plc"),
        address=_text(row, "st_endereco_cond"),
        zip_code=_text(row, "st_cep_cond"),
        city=_text(row, "st_cidade_cond"),
    )


def _normalize_accounts(rows: list[dict[str, Any]]) -> list[SourceAccount]:
    """A hierarquia está no código pontuado: o pai de `2.1.10` é `2.1`."""
    named = [
        (_text(row, "st_conta_cont"), _text(row, "st_descricao_cont")) for row in rows
    ]
    named = [(code, name) for code, name in named if code]
    codes = {code for code, _ in named}
    accounts = []
    for code, name in named:
        parent = code.rsplit(".", 1)[0] if "." in code else ""
        accounts.append(
            SourceAccount(
                code=code,
                name=name,
                parent_code=parent,
                orphan=bool(parent) and parent not in codes,
            )
        )
    return accounts


class SuperlogicaSource:
    source_name = "superlogica"

    def __init__(self, client: SuperlogicaClient) -> None:
        self._client = client

    def list_condominiums(self) -> list[SourceCondominium]:
        """Sem `id=-1` a API devolve só um condomínio; por isso a listagem é paginada."""
        found: dict[str, SourceCondominium] = {}
        for page in range(1, MAX_PAGES + 1):
            rows = self._client.get(
                "condominios/get",
                {"id": -1, "itensPorPagina": PAGE_SIZE, "pagina": page},
            )
            fresh = 0
            for row in rows:
                condominium = _normalize_condominium(row)
                if condominium.external_id not in found:
                    found[condominium.external_id] = condominium
                    fresh += 1
            # Página vazia é o fim; página sem nenhum id novo indica que a API
            # ignorou `pagina`.
            if fresh == 0:
                break
        else:
            raise SourceError(
                "O Superlógica excedeu o limite de páginas de condomínios."
            )
        return list(found.values())

    def list_charts(self) -> list[SourceChart]:
        """Planos usados pelos condomínios. A listagem de planos aceita qualquer id."""
        used = sorted({c.chart_external_id for c in self.list_condominiums()} - {""})
        if not used:
            return []
        rows = self._client.get("planocontas", {"ID_PLANOCONTA_PLC": used[0]})
        charts = []
        for row in rows:
            external_id = _text(row, "id_planoconta_plc")
            if external_id in used:
                name = next((n for f in _CHART_NAME_FIELDS if (n := _text(row, f))), "")
                charts.append(SourceChart(external_id, name or f"Plano {external_id}"))
        return charts

    def list_accounts(self, chart_external_id: str) -> list[SourceAccount]:
        rows = self._client.get("planocontas", {"id": chart_external_id})
        return _normalize_accounts(rows)
