"""Aprende regras de fornecedor com as despesas que o ERP já tem lançadas."""

from __future__ import annotations

import collections
import uuid
from dataclasses import dataclass
from datetime import date

from accounting.models import ChartOfAccounts, LedgerAccount, SupplierRule
from condominiums.text import normalize_text
from django.db import transaction

from erp_import.sources.base import RegistrySource, SourceExpense


@dataclass
class HistorySummary:
    expenses: int = 0
    rules_created: int = 0
    rules_updated: int = 0
    name_rules: int = 0
    skipped_manual: int = 0
    skipped_unmapped: int = 0


def _rule_key(expense: SourceExpense) -> tuple[str, str] | None:
    """(CNPJ/CPF, trecho): pelo documento do fornecedor; sem ele, pelo nome."""
    if expense.supplier_tax_id:
        return expense.supplier_tax_id, ""
    name = normalize_text(expense.supplier_name)
    if SupplierRule.MIN_NAME_LENGTH <= len(name) <= SupplierRule.MAX_NAME_LENGTH:
        return "", name
    return None


def leaf_accounts() -> dict[tuple, LedgerAccount]:
    """Contas ativas e analíticas, por (plano, código)."""
    parents = set(
        LedgerAccount.objects.exclude(parent=None).values_list("parent_id", flat=True)
    )
    return {
        (a.chart_id, a.code): a
        for a in LedgerAccount.objects.filter(is_active=True).exclude(pk__in=parents)
    }


def resolve_expenses(
    expenses: list[SourceExpense], source_name: str
) -> tuple[list[tuple[tuple, uuid.UUID]], int]:
    """Cada despesa utilizável como ((plano, CNPJ/CPF, trecho), conta); e quantas não foram."""
    charts = {
        c.external_id: c
        for c in ChartOfAccounts.objects.filter(
            external_source=source_name, is_active=True
        ).exclude(external_id="")
    }
    accounts = leaf_accounts()
    resolved: list[tuple[tuple, uuid.UUID]] = []
    unusable = 0
    for expense in expenses:
        key = _rule_key(expense)
        chart = charts.get(expense.chart_external_id)
        account = accounts.get((chart.id, expense.account_code)) if chart else None
        if key is None or account is None:
            unusable += 1
            continue
        resolved.append(((chart.id, *key), account.id))
    return resolved, unusable


def tally_expenses(
    expenses: list[SourceExpense], source_name: str
) -> tuple[dict[tuple, collections.Counter], int]:
    """Conta, por (plano, CNPJ, trecho), quantas vezes cada conta foi usada."""
    resolved, unusable = resolve_expenses(expenses, source_name)
    counts: dict[tuple, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for key, account_id in resolved:
        counts[key][account_id] += 1
    return counts, unusable


def seed_rules_from_history(
    source: RegistrySource, date_from: date, date_to: date
) -> HistorySummary:
    """Cria ou atualiza uma regra por fornecedor (ou nome) e plano, com a conta mais usada
    e a evidência.

    Regra manual ou aprendida com o analista nunca é sobrescrita. Despesa de plano ou conta
    que ainda não foi importada (ou que não é analítica) é ignorada."""
    expenses = source.list_expenses(date_from, date_to)
    counts, unmapped = tally_expenses(expenses, source.source_name)
    summary = HistorySummary(expenses=len(expenses), skipped_unmapped=unmapped)
    by_id = {a.id: a for a in leaf_accounts().values()}

    with transaction.atomic():
        for (chart_id, tax_id, keyword), tally in counts.items():
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
                chart_id=chart_id,
                condominium=None,
                supplier_tax_id=tax_id,
                keyword=keyword,
            ).first()
            if existing is None:
                SupplierRule.objects.create(
                    chart_id=chart_id,
                    supplier_tax_id=tax_id,
                    keyword=keyword,
                    **fields,
                )
                summary.rules_created += 1
            elif existing.origin == SupplierRule.Origin.HISTORY:
                for name, value in fields.items():
                    setattr(existing, name, value)
                existing.save()
                summary.rules_updated += 1
            else:
                summary.skipped_manual += 1
            summary.name_rules += not tax_id
    return summary
