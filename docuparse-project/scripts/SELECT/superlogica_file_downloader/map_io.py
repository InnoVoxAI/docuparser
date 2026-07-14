"""Leitura, validação e reescrita do mapa (entrada da Fase B).

- :func:`load_map` lê o ``mapa_download.csv`` (ou ``.json``) e valida as colunas
  essenciais; ausência/ilegibilidade → :class:`MapError` (E-01, fatal).
- :func:`write_map` reescreve o mapa **atomicamente** (tmp → ``os.replace``),
  preservando todas as colunas de conteúdo (FR-004) e refletindo o ``status``
  atualizado — base da retomada (RN-4/D7).
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path

# Colunas do contrato mapa-download.md (spec 012), na ordem canônica.
MAP_COLUMNS: tuple[str, ...] = (
    "url_download",
    "nome_arquivo",
    "fornecedor",
    "categoria_bruta",
    "complemento",
    "pasta_destino",
    "hyperlink_origem",
    "pdf_origem",
    "status",
)
# Mínimo para a Fase B conseguir trabalhar.
ESSENTIAL_COLUMNS: tuple[str, ...] = (
    "url_download",
    "nome_arquivo",
    "pasta_destino",
    "status",
)

STATUS_PENDENTE = "pendente"
STATUS_BAIXADO = "baixado"
STATUS_ERRO = "erro"


class MapError(RuntimeError):
    """Mapa ausente/ilegível ou sem colunas essenciais (E-01, fatal)."""


@dataclass
class MapRow:
    """Uma linha do mapa. A Fase B lê tudo e escreve apenas ``status``."""

    url_download: str
    nome_arquivo: str
    fornecedor: str = ""
    categoria_bruta: str = ""
    complemento: str = ""
    pasta_destino: str = ""
    hyperlink_origem: str = ""
    pdf_origem: str = ""
    status: str = STATUS_PENDENTE

    @classmethod
    def from_dict(cls, d: dict) -> MapRow:
        status = (d.get("status") or STATUS_PENDENTE).strip() or STATUS_PENDENTE
        return cls(
            url_download=(d.get("url_download") or "").strip(),
            nome_arquivo=(d.get("nome_arquivo") or "").strip(),
            fornecedor=d.get("fornecedor") or "",
            categoria_bruta=d.get("categoria_bruta") or "",
            complemento=d.get("complemento") or "",
            pasta_destino=(d.get("pasta_destino") or "").strip(),
            hyperlink_origem=d.get("hyperlink_origem") or "",
            pdf_origem=d.get("pdf_origem") or "",
            status=status,
        )


def _check_columns(header: list[str], path: Path) -> None:
    missing = [c for c in ESSENTIAL_COLUMNS if c not in header]
    if missing:
        raise MapError(f"colunas essenciais ausentes em {path}: {', '.join(missing)}")


def load_map(path: str | Path, fmt: str = "csv") -> list[MapRow]:
    """Carrega o mapa. Ausente/vazio/ilegível ou sem colunas → :class:`MapError`."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise MapError(f"mapa ausente ou vazio: {path} — rode a Fase A primeiro.")
    try:
        return _parse_csv(path) if fmt != "json" else _parse_json(path)
    except MapError:
        raise
    except Exception as exc:  # noqa: BLE001 — arquivo corrompido/inválido
        raise MapError(f"mapa ilegível: {path}: {exc}") from exc


def _parse_csv(path: Path) -> list[MapRow]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        _check_columns(reader.fieldnames or [], path)
        return [MapRow.from_dict(row) for row in reader]


def _parse_json(path: Path) -> list[MapRow]:
    rows: list[MapRow] = []
    checked = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not checked:
            _check_columns(list(obj.keys()), path)
            checked = True
        rows.append(MapRow.from_dict(obj))
    if not checked:
        raise MapError(f"mapa JSON vazio: {path}")
    return rows


def write_map(path: str | Path, fmt: str, rows: list[MapRow]) -> None:
    """Reescreve o mapa atomicamente com o ``status`` atualizado (D7)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    if fmt == "json":
        _dump_json(tmp, rows)
    else:
        _dump_csv(tmp, rows)
    os.replace(tmp, path)


def _dump_csv(tmp: Path, rows: list[MapRow]) -> None:
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(MAP_COLUMNS)
        for row in rows:
            writer.writerow([getattr(row, col) for col in MAP_COLUMNS])


def _dump_json(tmp: Path, rows: list[MapRow]) -> None:
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            obj = {col: getattr(row, col) for col in MAP_COLUMNS}
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
