"""Nenhum teste deste pacote pode falar com o Superlógica de verdade.

Os tokens dos tenants são de um ambiente real, então qualquer envio HTTP que não passe
por uma sessão falsa derruba o teste.
"""

from __future__ import annotations

import pytest
import requests


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(self, request, **kwargs):  # noqa: ANN001
        raise AssertionError(
            f"Chamada HTTP real bloqueada no teste: {request.method} {request.url}"
        )

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", refuse)
