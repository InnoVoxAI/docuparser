"""Erros do lançamento no ERP.

Cada erro traz um código estável (para a tela e para os testes) e uma mensagem em
português para o analista. A mensagem nunca carrega corpo de requisição ou de
resposta do ERP.
"""

from __future__ import annotations

from typing import Any


class ExportError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        # Vale tentar de novo sem o analista mexer no documento (rede, 5xx).
        self.retryable = retryable
        # O ERP pode ter aceitado o pedido mesmo sem responder: antes de reenviar,
        # é preciso consultar o ERP (reconciliação), nunca reenviar às cegas.
        self.outcome_unknown = outcome_unknown

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "outcome_unknown": self.outcome_unknown,
        }


class DraftInvalid(Exception):
    """O documento não tem o que o ERP exige. Reúne todos os problemas de uma vez."""

    def __init__(self, errors: list[ExportError]) -> None:
        super().__init__("; ".join(error.message for error in errors))
        self.errors = errors
