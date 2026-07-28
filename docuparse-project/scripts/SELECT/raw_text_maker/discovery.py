"""Varredura da árvore de origem e mapeamento documento → ``.txt`` de destino.

Espelha a árvore: ``<source>/<categoria>/<nome>.pdf`` vira
``<output>/<categoria>/<nome>.txt`` (mesmo nome, só a extensão muda). Categorias
aninhadas são preservadas. Etapa pura — não toca em rede.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from raw_text_maker.config import SOURCE_EXTENSIONS, TEXT_SUFFIX

if TYPE_CHECKING:
    from raw_text_maker.config import Config


class DiscoveryError(RuntimeError):
    """Árvore de origem ausente ou ilegível (fatal)."""


@dataclass(frozen=True)
class Job:
    """Um documento a processar e o ``.txt`` que ele deve produzir."""

    source: Path
    dest: Path
    categoria: str
    rel: str  # caminho de origem relativo à raiz, para logs e CSV


def _is_document(path: Path) -> bool:
    # Ignora ocultos (e ``.part`` da Fase B, que é um download interrompido).
    return (
        path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SOURCE_EXTENSIONS
    )


def discover_jobs(config: Config) -> tuple[list[Job], list[Job]]:
    """Mapeia a árvore de origem.

    Retorna ``(jobs, colisoes)``. Uma colisão é um documento cujo ``.txt`` de
    destino já foi reivindicado por outro documento (mesmo nome, extensões
    diferentes) — processá-lo sobrescreveria o texto do primeiro em silêncio,
    então ele é reportado como erro em vez de executado.
    """
    root = config.source_root
    if not root.is_dir():
        raise DiscoveryError(f"árvore de origem não encontrada: {root}")

    jobs: list[Job] = []
    colisoes: list[Job] = []
    claimed: dict[Path, Job] = {}

    for path in sorted(root.rglob("*"), key=lambda p: str(p).lower()):
        if not _is_document(path):
            continue
        rel_path = path.relative_to(root)
        # ``with_suffix`` troca só a última extensão: "NF 113,95.pdf" → "NF 113,95.txt".
        dest = (config.output_root / rel_path).with_suffix(TEXT_SUFFIX)
        parent = rel_path.parent
        job = Job(
            source=path,
            dest=dest,
            categoria=str(parent) if parent != Path(".") else "",
            rel=str(rel_path),
        )
        if dest in claimed:
            colisoes.append(job)
            continue
        claimed[dest] = job
        jobs.append(job)

    return jobs, colisoes


def split_pending(jobs: list[Job]) -> tuple[list[Job], list[Job]]:
    """Separa ``(concluidos, pendentes)`` para a retomada.

    Concluído = ``.txt`` presente e **não vazio**. Um arquivo de 0 byte significa
    que a run anterior morreu no meio ou que o OCR não devolveu texto; nesses
    casos vale reprocessar em vez de dar o documento por pronto.
    """
    concluidos: list[Job] = []
    pendentes: list[Job] = []
    for job in jobs:
        if job.dest.exists() and job.dest.stat().st_size > 0:
            concluidos.append(job)
        else:
            pendentes.append(job)
    return concluidos, pendentes
