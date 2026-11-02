from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from condominiums.tax_ids import is_valid_cpf
from condominiums.text import normalize_text
from django.db.models import Q

from accounting.classification.facts import Classification, DocumentFacts
from accounting.models import LedgerAccount, SupplierRule

if TYPE_CHECKING:
    from condominiums.models import Condominium


class Rule(Protocol):
    rule_id: str

    def apply(
        self, facts: DocumentFacts, condominium: Condominium
    ) -> Classification | None: ...


class SupplierRuleLookup:
    """Cadastro de fornecedores: regras do plano do condomínio, e as só dele (`SupplierRule`)."""

    rule_id = "supplier"

    def apply(
        self, facts: DocumentFacts, condominium: Condominium
    ) -> Classification | None:
        tax_id = facts.supplier_tax_id(condominium.cnpj)
        if tax_id is None or condominium.chart_of_accounts_id is None:
            return None
        rules = SupplierRule.objects.filter(
            Q(condominium=condominium) | Q(condominium__isnull=True),
            chart_id=condominium.chart_of_accounts_id,
            supplier_tax_id=tax_id,
            is_active=True,
            ledger_account__is_active=True,
        ).select_related("ledger_account")
        # A regra só do condomínio vence a do plano; com trecho, vence a sem trecho.
        for rule in sorted(
            rules,
            key=lambda r: (r.condominium_id is not None, len(r.keyword)),
            reverse=True,
        ):
            if rule.keyword and normalize_text(rule.keyword) not in facts.text:
                continue
            if not rule.is_confident:
                continue
            reason = f"fornecedor {tax_id}"
            if rule.keyword:
                reason += f" com o trecho '{rule.keyword}'"
            if rule.origin == SupplierRule.Origin.HISTORY:
                reason += f" (histórico: {rule.evidence_count} de {rule.evidence_total} lançamentos)"
            return Classification(rule.ledger_account, self.rule_id, reason)
        return None


class NatureRule:
    """Reconhece o documento pelo conteúdo e usa a conta marcada com `nature`."""

    rule_id: str
    nature: str
    reason: str

    def matches(self, facts: DocumentFacts) -> bool:
        raise NotImplementedError

    def apply(
        self, facts: DocumentFacts, condominium: Condominium
    ) -> Classification | None:
        if not self.matches(facts):
            return None
        if condominium.chart_of_accounts_id is None:
            return None
        account = LedgerAccount.objects.filter(
            chart_id=condominium.chart_of_accounts_id,
            nature=self.nature,
            is_active=True,
        ).first()
        if account is None:
            return None
        return Classification(account, self.rule_id, self.reason)


class SocialSecurityRule(NatureRule):
    rule_id = "inss"
    nature = LedgerAccount.Nature.INSS
    reason = "DARF ou GPS de contribuição previdenciária"

    _GUIDE = re.compile(
        r"DOCUMENTO DE ARRECADACAO DE RECEITAS FEDERAIS|GUIA DA PREVIDENCIA SOCIAL"
    )
    # Denominações de receita da DCTFWeb: "CP SEGURADOS", "CONTRIB PREV ...".
    _SOCIAL_SECURITY = re.compile(
        r"\bCP (SEGURADOS|PATRONAL|TERCEIROS)\b|\bCONTRIB\w* PREV"
    )

    def matches(self, facts: DocumentFacts) -> bool:
        return bool(
            self._GUIDE.search(facts.text) and self._SOCIAL_SECURITY.search(facts.text)
        )


class FgtsRule(NatureRule):
    rule_id = "fgts"
    nature = LedgerAccount.Nature.FGTS
    reason = "guia de recolhimento do FGTS"

    _GUIDE = re.compile(r"GUIA DO FGTS|FGTS DIGITAL|GUIA DE RECOLHIMENTO DO FGTS")

    def matches(self, facts: DocumentFacts) -> bool:
        return bool(self._GUIDE.search(facts.text))


class IndividualReceiptRule(NatureRule):
    """Recibo assinado por pessoa física ainda sem regra de fornecedor (ex. RPA)."""

    rule_id = "recibo_pessoa_fisica"
    nature = LedgerAccount.Nature.SERVICO_PESSOA_FISICA
    reason = "recibo de pessoa física"

    _RECEIPT = re.compile(r"\bRECEBI\b")
    # Recibo de pensão alimentícia não é prestação de serviço.
    _ALIMONY = re.compile(r"\bPENSAO\b")

    def matches(self, facts: DocumentFacts) -> bool:
        text = facts.text
        return (
            bool(self._RECEIPT.search(text))
            and not self._ALIMONY.search(text)
            and any(is_valid_cpf(tax_id) for tax_id in facts.tax_ids_in_text)
        )


# Ordem de avaliação: o cadastro explícito do operador vence as regras de conteúdo.
RULES: tuple[Rule, ...] = (
    SupplierRuleLookup(),
    SocialSecurityRule(),
    FgtsRule(),
    IndividualReceiptRule(),
)
