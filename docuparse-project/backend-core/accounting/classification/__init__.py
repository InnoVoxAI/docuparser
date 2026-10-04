"""Motor de classificação de documentos em contas do plano de contas."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from accounting.classification.facts import Classification, DocumentFacts
from accounting.classification.rules import RULES, Rule

if TYPE_CHECKING:
    from condominiums.models import Condominium

__all__ = ["Classification", "DocumentFacts", "Rule", "RULES", "classify"]


def classify(
    facts: DocumentFacts, condominium: Condominium, rules: Iterable[Rule] = RULES
) -> Classification | None:
    """Aplica as regras em ordem; a primeira que encontrar uma conta vence."""
    for rule in rules:
        classification = rule.apply(facts, condominium)
        if classification is not None:
            return classification
    return None
