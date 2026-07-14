"""Saídas da Fase B: CSV final (entregável) e relatório de erros.

- :class:`FinalCsvWriter` — **append incremental** (RN-5) com dedup por
  ``caminho_local`` (chave única por linha; RN-6), sobrevive a interrupção.
  Acumula entre execuções (base da retomada).
- :class:`ErrorReportWriter` — reescrito a cada execução (reflete o estado da
  **última** run), append incremental durante a run. Sinaliza expiração (E-04).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from superlogica_file_downloader.config import ERROR_COLUMNS, FINAL_COLUMNS


@dataclass
class FinalRow:
    nome_arquivo: str
    hyperlink_origem: str
    categoria: str
    caminho_local: str
    pasta_destino: str
    fornecedor: str


@dataclass
class ErrorRecord:
    url_download: str
    motivo: str
    tentativas: int
    possivel_expiracao: bool
    nome_arquivo: str = ""
    pdf_origem: str = ""


class FinalCsvWriter:
    """Writer append-only do CSV final, dedup por ``caminho_local``."""

    def __init__(self, path: str | Path, columns: tuple[str, ...] = FINAL_COLUMNS) -> None:
        self.path = Path(path)
        self.columns = columns
        self._seen: set[str] = set()
        self._fh = None
        self._writer = None
        self._load_existing()

    def _load_existing(self) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        with open(self.path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key = (row.get("caminho_local") or "").strip()
                if key:
                    self._seen.add(key)

    def __enter__(self) -> FinalCsvWriter:
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        if is_new:
            self._writer.writerow(self.columns)
            self._fh.flush()
        return self

    def __exit__(self, *exc) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def already_written(self, caminho_local: str) -> bool:
        return caminho_local in self._seen

    def write(self, row: FinalRow) -> bool:
        """Append + flush. Retorna ``False`` se ``caminho_local`` já existia (dedup)."""
        if self._fh is None:
            raise RuntimeError("FinalCsvWriter usado fora do bloco 'with'.")
        if row.caminho_local in self._seen:
            return False
        self._writer.writerow([getattr(row, col) for col in self.columns])
        self._fh.flush()  # progresso em disco (sobrevive a interrupção)
        self._seen.add(row.caminho_local)
        return True


class ErrorReportWriter:
    """Writer do relatório de erros; **trunca** ao abrir (estado da última run)."""

    def __init__(self, path: str | Path, columns: tuple[str, ...] = ERROR_COLUMNS) -> None:
        self.path = Path(path)
        self.columns = columns
        self._fh = None
        self._writer = None

    def __enter__(self) -> ErrorReportWriter:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(self.columns)
        self._fh.flush()
        return self

    def __exit__(self, *exc) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def write(self, record: ErrorRecord) -> None:
        if self._fh is None:
            raise RuntimeError("ErrorReportWriter usado fora do bloco 'with'.")
        values = {
            "url_download": record.url_download,
            "motivo": record.motivo,
            "tentativas": record.tentativas,
            "possivel_expiracao": "sim" if record.possivel_expiracao else "não",
            "nome_arquivo": record.nome_arquivo,
            "pdf_origem": record.pdf_origem,
        }
        self._writer.writerow([values[col] for col in self.columns])
        self._fh.flush()
