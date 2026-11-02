"""Mede o acerto das regras do histórico sem rótulo manual: aprende com o passado, testa no futuro."""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from datetime import date

from accounting.models import SupplierRule

from erp_import.history import resolve_expenses, tally_expenses
from erp_import.sources.base import SourceExpense


@dataclass
class Score:
    total: int = 0
    suggested: int = 0
    correct: int = 0

    @property
    def coverage(self) -> float:
        return self.suggested / self.total if self.total else 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.suggested if self.suggested else 0.0


@dataclass
class HoldoutReport:
    train: int = 0
    test: int = 0
    by_tax_id: Score = field(default_factory=Score)
    by_name: Score = field(default_factory=Score)
    unusable: int = 0


def _confident(tally: collections.Counter) -> bool:
    total = sum(tally.values())
    top = tally.most_common(1)[0][1]
    return (
        total >= SupplierRule.MIN_HISTORY_EVIDENCE
        and top / total >= SupplierRule.MIN_HISTORY_AGREEMENT
    )


def evaluate_holdout(
    expenses: list[SourceExpense],
    source_name: str,
    cutoff: date,
    until: date | None = None,
) -> HoldoutReport:
    """Regras do que veio antes de `cutoff`, testadas nas despesas de `cutoff` até `until`."""
    train = [e for e in expenses if e.posted_on and e.posted_on < cutoff]
    test = [
        e
        for e in expenses
        if e.posted_on
        and e.posted_on >= cutoff
        and (until is None or e.posted_on <= until)
    ]
    learned, _ = tally_expenses(train, source_name)
    resolved, unusable = resolve_expenses(test, source_name)
    report = HoldoutReport(train=len(train), test=len(test), unusable=unusable)
    for key, actual in resolved:
        score = report.by_tax_id if key[1] else report.by_name
        score.total += 1
        tally = learned.get(key)
        if tally and _confident(tally):
            score.suggested += 1
            score.correct += tally.most_common(1)[0][0] == actual
    return report
