"""Sanitização de nomes de arquivo e de pasta (Seção 5.3, E-08, E-09).

- ``url_decode``: reverte percent-encoding e ``+``→espaço (E-09), aplicado a
  valores vindos de URLs antes de tratá-los como texto legível.
- ``sanitize``: remove/substitui caracteres inválidos para sistema de arquivos,
  colapsa espaços e evita nomes vazios/reservados (E-08).

Acentuação legível é preservada (a remoção de acento é feita apenas na chave
canônica de categoria — ver ``categorizer``).
"""

from __future__ import annotations

import re
from urllib.parse import unquote_plus

# Caracteres visíveis inválidos para sistema de arquivos → substituídos por `_`.
_INVALID_VISIBLE = re.compile(r'[/\\:*?"<>|]')
# Caracteres de controle não-espaço → removidos.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f]")
_WHITESPACE = re.compile(r"\s+")

# Nomes reservados do Windows (comparação sem extensão, caixa-insensível).
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

DEFAULT_FALLBACK = "_sem_nome_"


def url_decode(value: str) -> str:
    """Reverte percent-encoding e ``+``→espaço (E-09)."""
    if not value:
        return ""
    return unquote_plus(value)


def sanitize(value: str | None, *, fallback: str = DEFAULT_FALLBACK) -> str:
    """Torna ``value`` seguro como nome de arquivo/pasta.

    Remove caracteres inválidos, colapsa espaços, apara pontas (inclusive
    pontos/espaços finais) e devolve ``fallback`` se o resultado ficar vazio ou
    colidir com um nome reservado.
    """
    if not value:
        return fallback
    # 1) normaliza espaços em branco (tab/newline viram espaço, colapsa runs).
    cleaned = _WHITESPACE.sub(" ", value)
    # 2) remove caracteres de controle restantes (não-espaço).
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    # 3) substitui caracteres visíveis inválidos por `_`.
    cleaned = _INVALID_VISIBLE.sub("_", cleaned).strip()
    # Windows não permite nome terminando em ponto ou espaço.
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        return fallback
    stem = cleaned.split(".", 1)[0].strip().upper()
    if stem in _RESERVED_NAMES:
        return fallback
    return cleaned
