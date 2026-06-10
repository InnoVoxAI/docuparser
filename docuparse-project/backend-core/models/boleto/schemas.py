from __future__ import annotations

import re

SCHEMA_ID = "boleto_default"

_KEYWORDS = [
    "boleto",
    "linha digitavel",
    "beneficiario",
    "pagador",
    "vencimento",
    "nosso numero",
    "valor",
]

_LINHA_DIGITAVEL_RE = re.compile(
    r"\b\d{5}\.?\d{5}\s+\d{5}\.?\d{6}\s+\d{5}\.?\d{6}\s+\d\s+\d{14}\b"
)
_BARCODE_RE = re.compile(r"\b\d{44}\b")
_THRESHOLD = 4


def score(raw_text: str) -> int:
    if not raw_text:
        return 0
    text = str(raw_text).lower()
    s = sum(1 for kw in _KEYWORDS if kw in text)
    if _LINHA_DIGITAVEL_RE.search(text):
        s += 3
    if _BARCODE_RE.search(text):
        s += 2
    return s


def is_likely(raw_text: str, threshold: int = _THRESHOLD) -> bool:
    return score(raw_text) >= threshold
