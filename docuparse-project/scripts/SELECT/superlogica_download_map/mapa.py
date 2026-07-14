"""Escrita incremental e idempotente do mapa de download.

- :class:`MapEntry` = uma linha do mapa (contrato ``contracts/mapa-download.md``).
- :class:`MapWriter` grava **linha a linha** (append + flush), sobrevive a
  interrupção (FR-015), deduplica por ``url_download`` (RN-6/FR-016) e valida a
  proveniência antes de gravar (FR-014/T027).

Formato ``csv`` (padrão) ou ``json`` (JSON Lines: um objeto por linha, também
appendável e idempotente).
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
STATUS_PENDENTE = "pendente"

# Campos que toda linha DEVE ter (proveniência + destino). ``categoria_bruta``
# pode ser vazia quando indeterminada — nesse caso ``pasta_destino`` é _A_Revisar.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "url_download",
    "nome_arquivo",
    "pasta_destino",
    "hyperlink_origem",
    "pdf_origem",
)


class ProvenanceError(ValueError):
    """Linha sem campos obrigatórios de proveniência/destino (FR-014)."""


@dataclass
class MapEntry:
    url_download: str
    nome_arquivo: str
    fornecedor: str
    categoria_bruta: str
    complemento: str
    pasta_destino: str
    hyperlink_origem: str
    pdf_origem: str
    status: str = STATUS_PENDENTE

    def as_row(self) -> list[str]:
        return [getattr(self, col) for col in MAP_COLUMNS]

    def missing_required(self) -> list[str]:
        return [f for f in _REQUIRED_FIELDS if not str(getattr(self, f)).strip()]


@dataclass
class MapWriter:
    """Writer append-only com deduplicação por ``url_download``."""

    path: Path
    fmt: str = "csv"
    _seen: set[str] = field(default_factory=set, init=False)
    _fh: object | None = field(default=None, init=False)
    _csv_writer: object | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._load_existing()

    def _load_existing(self) -> None:
        """Carrega as ``url_download`` já presentes para garantir idempotência."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        if self.fmt == "csv":
            with open(self.path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    url = (row.get("url_download") or "").strip()
                    if url:
                        self._seen.add(url)
        else:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    url = (json.loads(line).get("url_download") or "").strip()
                except json.JSONDecodeError:
                    continue
                if url:
                    self._seen.add(url)

    def __enter__(self) -> MapWriter:
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", newline="", encoding="utf-8")
        if self.fmt == "csv":
            self._csv_writer = csv.writer(self._fh)
            if is_new:
                self._csv_writer.writerow(MAP_COLUMNS)
                self._fh.flush()
        return self

    def __exit__(self, *exc) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def already_mapped(self, url_download: str) -> bool:
        return url_download in self._seen

    def write(self, entry: MapEntry) -> bool:
        """Grava a linha (append + flush). Retorna ``False`` se já existia (dedup).

        Levanta :class:`ProvenanceError` se faltar campo obrigatório.
        """
        missing = entry.missing_required()
        if missing:
            raise ProvenanceError(f"campos obrigatórios ausentes: {', '.join(missing)}")
        if entry.url_download in self._seen:
            return False
        if self._fh is None:
            raise RuntimeError("MapWriter usado fora do bloco 'with'.")
        if self.fmt == "csv":
            self._csv_writer.writerow(entry.as_row())
        else:
            self._fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        self._fh.flush()  # progresso em disco (sobrevive a interrupção)
        self._seen.add(entry.url_download)
        return True
