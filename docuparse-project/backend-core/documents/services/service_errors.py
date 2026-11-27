"""Erros tipados das chamadas HTTP do core para backend-ocr e langextract-service.

Os clientes (`ocr_client.py`, `langextract_client.py`) classificam a falha aqui, e
o `@task` do orquestrador só repete o que for `TransientServiceError` (via
`retry_on`). As duas chamadas são pagas (OpenRouter / LLM), então a regra é
conservadora: só conta como transitório o que garante que o pedido não foi
processado, ou que o serviço pediu explicitamente para tentar de novo.

- Transitório: `ConnectTimeout`, `ConnectionError`, HTTP 429, 502, 503, 504.
- Permanente: qualquer outro 4xx, HTTP 500, `ReadTimeout` e JSON inválido.

HTTP 500 é permanente porque o backend-ocr devolve 500 para *qualquer* erro do
OpenRouter, inclusive 400/401/402 (`openrouter_engine.py` levanta RuntimeError e
`api/routes/document.py` responde "Erro interno"). `ReadTimeout` é permanente
porque o pedido chegou: o OCR provavelmente rodou e foi cobrado.
"""

from __future__ import annotations

from typing import Any

import requests

TRANSIENT_STATUS_CODES = frozenset({429, 502, 503, 504})


class ServiceError(Exception):
    """Falha numa chamada a um serviço interno (backend-ocr, langextract)."""

    def __init__(
        self, service: str, message: str, *, status_code: int | None = None
    ) -> None:
        self.service = service
        self.status_code = status_code
        status = f" HTTP {status_code}" if status_code is not None else ""
        super().__init__(f"{service}{status}: {message}")


class TransientServiceError(ServiceError):
    """Vale tentar de novo: o pedido não foi processado ou o serviço pediu retry."""


class PermanentServiceError(ServiceError):
    """Repetir não muda o resultado (ou cobraria de novo uma chamada paga)."""


def request_json(service: str, method: str, url: str, **kwargs: Any) -> Any:
    """Faz a chamada e devolve o JSON, ou levanta um `ServiceError` classificado.

    A exceção original do `requests` fica em `__cause__`.
    """
    try:
        response = requests.request(method, url, **kwargs)
    except requests.ConnectionError as exc:
        # Inclui ConnectTimeout (subclasse de ConnectionError e de Timeout).
        raise TransientServiceError(service, str(exc)) from exc
    except requests.Timeout as exc:
        # Sobra ReadTimeout: o serviço recebeu o pedido e pode tê-lo processado.
        raise PermanentServiceError(service, str(exc)) from exc
    except requests.RequestException as exc:
        raise PermanentServiceError(service, str(exc)) from exc

    if response.status_code >= 400:
        error_cls = (
            TransientServiceError
            if response.status_code in TRANSIENT_STATUS_CODES
            else PermanentServiceError
        )
        raise error_cls(service, response.text[:400], status_code=response.status_code)

    try:
        return response.json()
    except ValueError as exc:
        raise PermanentServiceError(
            service,
            f"resposta não é JSON válido: {response.text[:200]}",
            status_code=response.status_code,
        ) from exc
