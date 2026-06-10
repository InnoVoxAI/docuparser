from __future__ import annotations

import re
from dataclasses import dataclass


LAYOUTS = {
    "boleto_caixa",
    "boleto_bb",
    "boleto_bradesco",
    "fatura_energia",
    "fatura_condominio",
    "generic",
}


@dataclass(frozen=True)
class LayoutClassification:
    layout: str
    confidence: float
    requires_human_validation: bool


def classify_layout(raw_text: str, document_type: str = "unknown") -> LayoutClassification:
    text = _normalize(raw_text)
    scores = {
        "boleto_caixa": _score_boleto_caixa(text),
        "boleto_bb": _score_boleto_bb(text),
        "boleto_bradesco": _score_boleto_bradesco(text),
        "fatura_energia": _score_fatura_energia(text),
        "fatura_condominio": _score_fatura_condominio(text),
    }
    layout, confidence = max(scores.items(), key=lambda item: item[1])

    if confidence < 0.45:
        layout = "generic"
        confidence = 0.35 if text else 0.0

    return LayoutClassification(
        layout=layout,
        confidence=round(min(confidence, 0.99), 2),
        requires_human_validation=confidence < 0.7,
    )


def _normalize(raw_text: str) -> str:
    return re.sub(r"\s+", " ", (raw_text or "").lower()).strip()


def _score_boleto_caixa(text: str) -> float:
    return _weighted_score(
        text,
        {
            "caixa economica federal": 0.35,
            "104": 0.15,
            "linha digitavel": 0.2,
            "cedente": 0.1,
            "boleto": 0.1,
            "vencimento": 0.1,
        },
    )


def _score_boleto_bb(text: str) -> float:
    return _weighted_score(
        text,
        {
            "banco do brasil": 0.35,
            "001": 0.15,
            "linha digitavel": 0.2,
            "cedente": 0.1,
            "boleto": 0.1,
            "vencimento": 0.1,
        },
    )


def _score_boleto_bradesco(text: str) -> float:
    return _weighted_score(
        text,
        {
            "bradesco": 0.35,
            "237": 0.15,
            "linha digitavel": 0.2,
            "beneficiario": 0.1,
            "boleto": 0.1,
            "vencimento": 0.1,
        },
    )


def _score_fatura_energia(text: str) -> float:
    return _weighted_score(
        text,
        {
            "energia eletrica": 0.25,
            "kwh": 0.2,
            "unidade consumidora": 0.2,
            "consumo": 0.15,
            "distribuidora": 0.1,
            "vencimento": 0.1,
        },
    )


def _score_fatura_condominio(text: str) -> float:
    return _weighted_score(
        text,
        {
            "condominio": 0.3,
            "unidade": 0.15,
            "rateio": 0.15,
            "assembleia": 0.1,
            "sindico": 0.1,
            "vencimento": 0.1,
            "boleto": 0.1,
        },
    )


def _weighted_score(text: str, terms: dict[str, float]) -> float:
    return sum(weight for term, weight in terms.items() if term in text)
