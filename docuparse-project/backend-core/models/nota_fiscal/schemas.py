from __future__ import annotations

import re

SCHEMA_ID = "nota_fiscal_default"

_KEYWORDS = [
    "nota fiscal",
    "nf-e",
    "nfe",
    "chave de acesso",
    "icms",
    "ipi",
    "pis",
    "cofins",
    "iss",
    "tomador",
    "fornecedor",
    "descricao",
    "quantidade",
    "valor unitario",
    "valor total",
    "produtos",
    "servicos",
]

_ACCESS_KEY_RE = re.compile(r"\b\d{44}\b")
_THRESHOLD = 4


def score(raw_text: str) -> int:
    if not raw_text:
        return 0
    text = str(raw_text).lower()
    s = sum(1 for kw in _KEYWORDS if kw in text)
    if _ACCESS_KEY_RE.search(text):
        s += 3
    return s


def is_likely(raw_text: str, threshold: int = _THRESHOLD) -> bool:
    return score(raw_text) >= threshold
