"""Escritor do Superlógica: o único código que envia dados ao ERP.

Separado do `SuperlogicaClient` (que só faz GET) de propósito: a trava de somente
leitura da importação continua intacta.

- Lista fechada de escritas: qualquer outro método ou caminho é recusado antes da rede.
- Nenhuma retentativa automática no POST: reenviar às cegas pode lançar a despesa duas
  vezes. Quem decide reenviar é o conector, depois de consultar o ERP.
- Nunca registra token, corpo da requisição nem corpo da resposta, nem os devolve nas
  mensagens de erro.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from erp_export.errors import ExportError
from erp_export.payload import EXPENSE_PATH

logger = logging.getLogger(__name__)

# Única escrita permitida. Ampliar esta lista exige um novo item do épico.
ALLOWED_WRITES: frozenset[tuple[str, str]] = frozenset({("POST", EXPENSE_PATH)})

# Chaves em que o Superlógica pode devolver o id da despesa criada (a conferir no spike).
_ID_KEYS = ("id_despesa_des", "ID_DESPESA_DES", "id")


class WriteNotAllowed(RuntimeError):
    """Método ou caminho fora da lista fechada de escritas."""


@dataclass(frozen=True)
class WriteResult:
    external_id: str
    status_code: int


class SuperlogicaWriter:
    def __init__(
        self,
        app_token: str,
        access_token: str,
        base_url: str,
        *,
        session: requests.Session | None = None,
        timeout: float = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        # Sem HTTPAdapter com retry: o POST nunca é reenviado pela biblioteca.
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "app_token": app_token,
                "access_token": access_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def post(self, path: str, body: dict[str, Any]) -> WriteResult:
        normalized = path.strip("/")
        if ("POST", normalized) not in ALLOWED_WRITES:
            raise WriteNotAllowed(f"Escrita não permitida: POST {normalized}.")

        url = f"{self._base_url}/{normalized}"
        try:
            response = self._session.request(
                "POST", url, json=body, timeout=self._timeout
            )
        except requests.RequestException as exc:
            # Só o tipo do erro: a mensagem da biblioteca pode ecoar a requisição.
            logger.warning(
                "superlogica_write path=%s error=%s", normalized, type(exc).__name__
            )
            raise ExportError(
                "network_error",
                "Não foi possível falar com o Superlógica. O pedido pode ou não ter sido aceito.",
                retryable=True,
                outcome_unknown=True,
            ) from None

        status = response.status_code
        logger.info("superlogica_write path=%s status=%s", normalized, status)
        if status in (401, 403):
            raise ExportError(
                "auth_rejected",
                f"O Superlógica recusou as credenciais (HTTP {status}).",
            )
        if status == 429 or status >= 500:
            raise ExportError(
                "erp_unavailable",
                f"O Superlógica não conseguiu processar agora (HTTP {status}). "
                "O pedido pode ou não ter sido aceito.",
                retryable=True,
                outcome_unknown=True,
            )
        if not response.ok:
            raise ExportError(
                "erp_rejected",
                f"O Superlógica recusou os dados da despesa (HTTP {status}).",
            )
        return WriteResult(self._read_id(response), status)

    @staticmethod
    def _read_id(response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            data = data["data"]
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict):
            for key in _ID_KEYS:
                value = data.get(key)
                if value not in (None, ""):
                    return str(value)
        # Aceito, mas sem id legível: não dá para marcar como enviado com segurança.
        raise ExportError(
            "unexpected_response",
            "O Superlógica respondeu, mas não foi possível ler o id da despesa criada.",
            retryable=True,
            outcome_unknown=True,
        )
