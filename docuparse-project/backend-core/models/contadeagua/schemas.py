from __future__ import annotations

SCHEMA_ID = "conta_agua_default"

_KEYWORDS = [
    "fatura",
    "água",
    "agua",
    "esgoto",
    "consumo",
    "matrícula",
    "matricula",
    "hidrômetro",
    "hidrometro",
    "tarifa",
    "concessionaria",
    "compesa",
    "sabesp",
    "cedae",
    "embasa",
    "copasa",
    "sanepar",
    "cagece",
    "leitura",
    "economia",
]

_THRESHOLD = 3


def score(raw_text: str) -> int:
    if not raw_text:
        return 0
    text = str(raw_text).lower()
    return sum(1 for kw in _KEYWORDS if kw in text)


def is_likely(raw_text: str, threshold: int = _THRESHOLD) -> bool:
    return score(raw_text) >= threshold
