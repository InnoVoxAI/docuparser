"""Relatório de exceções (fail-soft) e utilidades de saída secundária.

O :class:`ExceptionReport` acumula ocorrências não-fatais durante a execução e
as grava em ``fase_a_relatorio.csv`` para revisão humana (FR-022). A passada de
reconhecimento (``--recon``) grava seu inventário via :func:`write_categories`.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPORT_HEADER = ("tipo", "origem", "detalhe", "acao_tomada")
CATEGORIES_HEADER = ("categoria_bruta", "chave_canonica", "pasta_destino_proposta")


@dataclass(frozen=True)
class ExceptionRecord:
    tipo: str
    origem: str
    detalhe: str
    acao_tomada: str


@dataclass
class ExceptionReport:
    """Coletor em memória das exceções fail-soft."""

    records: list[ExceptionRecord] = field(default_factory=list)

    def add(self, tipo: str, origem: str, detalhe: str, acao_tomada: str) -> None:
        self.records.append(ExceptionRecord(tipo, origem, detalhe, acao_tomada))

    def counts_by_type(self) -> dict[str, int]:
        return dict(Counter(r.tipo for r in self.records))

    def __len__(self) -> int:
        return len(self.records)

    def write_csv(self, path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(REPORT_HEADER)
            for r in self.records:
                writer.writerow([r.tipo, r.origem, r.detalhe, r.acao_tomada])


def write_categories(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """Grava o inventário da passada de reconhecimento (``categorias_encontradas.csv``)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CATEGORIES_HEADER)
        writer.writerows(rows)
