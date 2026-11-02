"""Aprende regras de fornecedor com as despesas que o ERP já tem lançadas."""

from __future__ import annotations

import collections
from dataclasses import dataclass
from datetime import date

from accounting.models import ChartOfAccounts, LedgerAccount, SupplierRule
from django.db import transaction

from erp_import.sources.base import RegistrySource


@dataclass
class HistorySummary:
    expenses: int = 0
    rules_created: int = 0
    rules_updated: int = 0
    skipped_manual: int = 0
    skipped_unmapped: int = 0


def seed_rules_from_history(
    source: RegistrySource, date_from: date, date_to: date
) -> HistorySummary:
    """Cria ou atualiza uma regra por fornecedor e plano, com a conta mais usada e a evidência.

    Regra manual ou aprendida com o analista nunca é sobrescrita. Despesa de plano ou conta
    que ainda não foi importada (ou que não é analítica) é ignorada."""
    expenses = source.list_expenses(date_from, date_to)
    summary = HistorySummary(expenses=len(expenses))

    charts = {
        c.external_id: c
        for c in ChartOfAccounts.objects.filter(
            external_source=source.source_name, is_active=True
        ).exclude(external_id="")
    }
    parents = set(
        LedgerAccount.objects.exclude(parent=None).values_list("parent_id", flat=True)
    )
    accounts = {
        (a.chart_id, a.code): a
        for a in LedgerAccount.objects.filter(is_active=True).exclude(pk__in=parents)
    }

    counts: dict[tuple, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for expense in expenses:
        chart = charts.get(expense.chart_external_id)
        account = accounts.get((chart.id, expense.account_code)) if chart else None
        if account is None:
            summary.skipped_unmapped += 1
            continue
        counts[(chart.id, expense.supplier_tax_id)][account.id] += 1

    by_id = {a.id: a for a in accounts.values()}
    with transaction.atomic():
        for (chart_id, tax_id), tally in counts.items():
            (top_id, top_count), *others = tally.most_common()
            fields = {
                "ledger_account": by_id[top_id],
                "origin": SupplierRule.Origin.HISTORY,
                "evidence_count": top_count,
                "evidence_total": sum(tally.values()),
                "alternatives": [
                    {"ledger_account_id": str(account_id), "count": count}
                    for account_id, count in others
                ],
                "is_active": True,
            }
            existing = SupplierRule.objects.filter(
                chart_id=chart_id, condominium=None, supplier_tax_id=tax_id, keyword=""
            ).first()
            if existing is None:
                SupplierRule.objects.create(
                    chart_id=chart_id, supplier_tax_id=tax_id, keyword="", **fields
                )
                summary.rules_created += 1
            elif existing.origin == SupplierRule.Origin.HISTORY:
                for name, value in fields.items():
                    setattr(existing, name, value)
                existing.save()
                summary.rules_updated += 1
            else:
                summary.skipped_manual += 1
    return summary
