"""Descobre a qual condomínio um documento pertence."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from condominiums.tax_ids import normalize_tax_id
from condominiums.text import normalize_text

from accounting.classification.facts import DocumentFacts

if TYPE_CHECKING:
    from condominiums.models import Condominium

# Campos extraídos com o CNPJ de quem paga: boleto e nota fiscal.
PAYER_FIELDS = ("cnpj_cpf_pagador", "cnpj_tomador")

Method = Literal["payer_tax_id", "text_tax_id", "name"]


@dataclass(frozen=True)
class Identification:
    condominium: Condominium
    method: Method
    reason: str


def _mentioned_terms(text: str, condominium: Condominium) -> list[str]:
    terms = (normalize_text(term) for term in (condominium.name, *condominium.aliases))
    return [
        term for term in terms if term and re.search(rf"\b{re.escape(term)}\b", text)
    ]


def identify_condominium(
    facts: DocumentFacts, condominiums: Iterable[Condominium]
) -> Identification | None:
    """Reconhece o condomínio pelo CNPJ do pagador, pelo CNPJ no texto ou pelo nome.

    Em caso de ambiguidade não adivinha: devolve None para o operador decidir.
    """
    active = [c for c in condominiums if c.is_active]
    by_cnpj = {c.cnpj: c for c in active if c.cnpj}

    for name in PAYER_FIELDS:
        tax_id = normalize_tax_id(str(facts.fields.get(name) or ""))
        if tax_id in by_cnpj:
            return Identification(by_cnpj[tax_id], "payer_tax_id", f"{name} {tax_id}")

    in_text = {by_cnpj[t] for t in facts.tax_ids_in_text if t in by_cnpj}
    if len(in_text) == 1:
        (condominium,) = in_text
        return Identification(
            condominium, "text_tax_id", f"CNPJ {condominium.cnpj} no documento"
        )
    if in_text:
        return None

    # Vence o condomínio cujo nome casou com o trecho mais longo ("EDIFICIO
    # PLATANO II" não é "EDIFICIO PLATANO").
    best: list[tuple[int, Condominium, str]] = []
    for condominium in active:
        terms = _mentioned_terms(facts.text, condominium)
        if terms:
            longest = max(terms, key=len)
            best.append((len(longest), condominium, longest))
    if not best:
        return None
    top = max(length for length, _, _ in best)
    winners = [(c, term) for length, c, term in best if length == top]
    if len(winners) != 1:
        return None
    condominium, term = winners[0]
    return Identification(condominium, "name", f"nome '{term}' no documento")
