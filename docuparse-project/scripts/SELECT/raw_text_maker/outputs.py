"""Saídas: o ``.txt`` de texto bruto e o relatório de erros.

- :func:`save_text_atomic` — grava em ``<destino>.part`` e promove com
  ``os.replace``. Uma interrupção (Ctrl-C no meio de um documento) nunca deixa um
  ``.txt`` com nome definitivo e conteúdo parcial, que a retomada leria como pronto.
- :class:`ErrorReportWriter` — **trunca ao abrir** (reflete o estado da última
  run: o que ainda falha) e faz append + flush a cada erro, conforme acontece.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from raw_text_maker.config import ERROR_COLUMNS


@dataclass
class ErrorRecord:
    arquivo_origem: str
    categoria: str
    motivo: str
    tentativas: int


def save_text_atomic(dest_path: str | Path, text: str) -> None:
    """Grava ``text`` (UTF-8) em ``<dest>.part`` e promove ao nome final."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)  # atômico: só agora o nome final existe
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


class ErrorReportWriter:
    """Writer do relatório de erros; trunca ao abrir, append durante a run."""

    def __init__(self, path: str | Path, columns: tuple[str, ...] = ERROR_COLUMNS) -> None:
        self.path = Path(path)
        self.columns = columns
        self.count = 0
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
            "arquivo_origem": record.arquivo_origem,
            "categoria": record.categoria,
            "motivo": record.motivo,
            "tentativas": record.tentativas,
            "ocorrido_em": datetime.now().isoformat(timespec="seconds"),
        }
        self._writer.writerow([values[col] for col in self.columns])
        self._fh.flush()  # erro em disco assim que acontece (sobrevive a interrupção)
        self.count += 1
