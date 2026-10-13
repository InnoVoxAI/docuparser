"""Normalização de texto para comparar nomes."""

from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    """Maiúsculas, sem acentos e com espaços colapsados, para comparar trechos."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.upper().split())
