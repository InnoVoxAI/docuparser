"""Contas candidatas de um documento, com a evidência de cada uma, para o analista escolher."""

from __future__ import annotations

import re
from typing import Any

from condominiums.text import normalize_text
from django.db.models import Q
from documents.models import Document

from accounting.models import LedgerAccount, SupplierRule
from accounting.services import facts_for_document

MAX_SUGGESTIONS = 6


def _matches(rule: SupplierRule, tax_id: str | None, text: str) -> bool:
    keyword = normalize_text(rule.keyword)
    if rule.supplier_tax_id:
        return rule.supplier_tax_id == tax_id and (not keyword or keyword in text)
    return bool(keyword) and re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def suggest_accounts(document: Document) -> dict[str, Any]:
    """Contas que o fornecedor do documento já usou, da mais para a menos usada.

    `confident` marca a que as regras pré-preenchem; as demais são só sugestões."""
    condominium = document.condominium
    empty: dict[str, Any] = {"supplier_known": False, "items": []}
    if condominium is None or condominium.chart_of_accounts_id is None:
        return empty

    facts = facts_for_document(document)
    tax_id = facts.supplier_tax_id(condominium.cnpj)
    rules = [
        rule
        for rule in SupplierRule.objects.filter(
            Q(condominium=condominium) | Q(condominium__isnull=True),
            chart_id=condominium.chart_of_accounts_id,
            is_active=True,
        ).select_related("ledger_account")
        if _matches(rule, tax_id, facts.text)
    ]
    if not rules:
        return {"supplier_known": tax_id is not None, "items": []}

    alternative_ids = {
        alt["ledger_account_id"] for rule in rules for alt in rule.alternatives
    }
    alternatives = {
        str(a.id): a
        for a in LedgerAccount.objects.filter(
            id__in=alternative_ids,
            chart_id=condominium.chart_of_accounts_id,
            is_active=True,
        )
    }

    items: dict[str, dict[str, Any]] = {}

    def offer(account: LedgerAccount, rule: SupplierRule, count: int, confident: bool):
        """Mesma conta em várias regras: fica a maior evidência, e vale se alguma é confiável."""
        key = str(account.id)
        current = items.get(key)
        if current is None or count > current["count"]:
            item = {
                "ledger_account": {
                    "id": key,
                    "code": account.code,
                    "name": account.name,
                },
                "count": count,
                "total": rule.evidence_total,
                "origin": rule.origin,
                "confident": confident,
            }
            if current is not None:
                item["confident"] = confident or current["confident"]
                if current["origin"] == SupplierRule.Origin.MANUAL:
                    item["origin"] = SupplierRule.Origin.MANUAL
            items[key] = item
        elif confident and not current["confident"]:
            current["confident"] = True
            if rule.origin == SupplierRule.Origin.MANUAL:
                current["origin"] = SupplierRule.Origin.MANUAL

    for rule in rules:
        if rule.ledger_account.is_active:
            offer(rule.ledger_account, rule, rule.evidence_count, rule.is_confident)
        for alt in rule.alternatives:
            account = alternatives.get(alt["ledger_account_id"])
            if account is not None:
                offer(account, rule, alt["count"], False)

    ordered = sorted(
        items.values(), key=lambda i: (i["confident"], i["count"]), reverse=True
    )
    return {"supplier_known": True, "items": ordered[:MAX_SUGGESTIONS]}
