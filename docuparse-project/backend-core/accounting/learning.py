"""O analista ensina o sistema: cada conta escolhida vira evidência para o fornecedor."""

from __future__ import annotations

import collections

from documents.models import Document

from accounting.models import LedgerAccount, SupplierRule
from accounting.services import facts_for_document

# Uma escolha do analista pesa o dobro de um lançamento do histórico; o mínimo de evidência
# é atingido com duas escolhas iguais (ou uma escolha mais um lançamento que concorde).
CHOICE_WEIGHT = 2


def learn_from_choice(
    document: Document, ledger_account: LedgerAccount, remember: bool = False
) -> SupplierRule | None:
    """Registra a escolha do analista na regra do fornecedor do documento, no plano.

    Com `remember` ("usar sempre"), vira regra cadastrada, que vale sempre. Sem ele, soma
    evidência: a conta só passa a ser pré-preenchida quando tiver evidência clara. Regra
    cadastrada à mão não é alterada por uma escolha avulsa. Devolve a regra, se houve."""
    condominium = document.condominium
    if (
        condominium is None
        or condominium.chart_of_accounts_id is None
        or ledger_account.chart_id != condominium.chart_of_accounts_id
    ):
        return None
    tax_id = facts_for_document(document).supplier_tax_id(condominium.cnpj)
    if tax_id is None:
        return None

    rule = SupplierRule.objects.filter(
        chart_id=condominium.chart_of_accounts_id,
        condominium=None,
        supplier_tax_id=tax_id,
        keyword="",
    ).first()

    if remember:
        fields = {
            "ledger_account": ledger_account,
            "origin": SupplierRule.Origin.MANUAL,
            "evidence_count": 0,
            "evidence_total": 0,
            "alternatives": [],
            "is_active": True,
        }
        if rule is None:
            return SupplierRule.objects.create(
                chart_id=condominium.chart_of_accounts_id,
                supplier_tax_id=tax_id,
                keyword="",
                **fields,
            )
        for name, value in fields.items():
            setattr(rule, name, value)
        rule.save()
        return rule

    if rule is not None and rule.origin == SupplierRule.Origin.MANUAL:
        return None

    tally: collections.Counter[str] = collections.Counter()
    if rule is not None:
        tally[str(rule.ledger_account_id)] = rule.evidence_count
        for alt in rule.alternatives:
            tally[alt["ledger_account_id"]] += alt["count"]
    tally[str(ledger_account.id)] += CHOICE_WEIGHT
    (top_id, top_count), *others = tally.most_common()
    fields = {
        "ledger_account": LedgerAccount.objects.get(pk=top_id),
        "origin": SupplierRule.Origin.LEARNED,
        "evidence_count": top_count,
        "evidence_total": sum(tally.values()),
        "alternatives": [
            {"ledger_account_id": account_id, "count": count}
            for account_id, count in others
        ],
        "is_active": True,
    }
    if rule is None:
        return SupplierRule.objects.create(
            chart_id=condominium.chart_of_accounts_id,
            supplier_tax_id=tax_id,
            keyword="",
            **fields,
        )
    for name, value in fields.items():
        setattr(rule, name, value)
    rule.save()
    return rule
