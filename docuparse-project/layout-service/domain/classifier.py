from __future__ import annotations

import re
from dataclasses import dataclass

LAYOUTS = {
    "nota_fiscal",
    "boleto_caixa",
    "boleto_bb",
    "boleto_bradesco",
    "boleto_generico",
    "fatura_energia",
    "fatura_condominio",
    "generic",
}


_BANK_BOLETO_LAYOUTS = ("boleto_caixa", "boleto_bb", "boleto_bradesco")
_LINHA_DIGITAVEL_RE = re.compile(
    r"\b\d{5}\.?\d{5}\s*\d{5}\.?\d{6}\s*\d{5}\.?\d{6}\s*\d\s*\d{14}\b"
)


@dataclass(frozen=True)
class LayoutClassification:
    layout: str
    confidence: float
    requires_human_validation: bool


def classify_layout(
    raw_text: str, document_type: str = "unknown"
) -> LayoutClassification:
    text = _normalize(raw_text)
    scores = {
        "nota_fiscal": _score_nota_fiscal(text),
        "boleto_caixa": _score_boleto_caixa(text),
        "boleto_bb": _score_boleto_bb(text),
        "boleto_bradesco": _score_boleto_bradesco(text),
        "boleto_generico": _score_boleto_generico(text),
        "fatura_energia": _score_fatura_energia(text),
        "fatura_condominio": _score_fatura_condominio(text),
    }
    layout, confidence = max(scores.items(), key=lambda item: item[1])

    # Banco identificado prevalece sobre o layout generico de boleto.
    if layout == "boleto_generico":
        bank_layout, bank_confidence = max(
            ((name, scores[name]) for name in _BANK_BOLETO_LAYOUTS),
            key=lambda item: item[1],
        )
        if bank_confidence >= 0.45:
            layout, confidence = bank_layout, bank_confidence

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


def _score_nota_fiscal(text: str) -> float:
    import re

    score = _weighted_score(
        text,
        {
            "nota fiscal": 0.30,
            "nf-e": 0.20,
            "nfs-e": 0.20,
            "nfe": 0.10,
            "chave de acesso": 0.15,
            "icms": 0.10,
            "valor total": 0.10,
            "tomador": 0.10,
            "fornecedor": 0.10,
            "prestador de servi": 0.10,
            "secretaria municipal": 0.10,
        },
    )
    if re.search(r"\b\d{44}\b", text):
        score += 0.25
    return min(score, 0.99)


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


def _score_boleto_generico(text: str) -> float:
    score = _weighted_score(
        text,
        {
            "ficha de compensa": 0.15,
            "linha digitavel": 0.10,
            "local de pagamento": 0.10,
            "benefici": 0.10,
            "cedente": 0.10,
            "pagador": 0.10,
            "nosso n": 0.10,
            "vencimento": 0.10,
            "boleto": 0.05,
        },
    )
    if _LINHA_DIGITAVEL_RE.search(text):
        score += 0.35
    return min(score, 0.99)


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
