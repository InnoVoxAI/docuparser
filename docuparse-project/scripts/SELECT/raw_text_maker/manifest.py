"""Registro do que já foi formatado — o gate de pendentes do modo ``--formatted``.

O ``.txt`` não carrega marca de origem: olhando o arquivo não dá para saber se o
conteúdo veio do texto **padrão** ou do **formatado**. Sem esse registro, cada
remessa nova faria o ``--formatted`` reenviar a árvore inteira ao docling para
reescrever, com conteúdo idêntico, o que já estava pronto.

Append-only com dedup por ``arquivo_origem`` (caminho relativo à raiz de origem),
gravado a cada sucesso — uma interrupção não perde o que já foi formatado.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from raw_text_maker.config import MANIFEST_COLUMNS

# Marca de entrada semeada a partir de uma árvore formatada antes deste registro
# existir (ver ``--seed-formatted``): não houve chamada ao backend.
SEEDED_ENGINE = "(semeado)"


class FormattedManifest:
    """Writer append-only do manifesto, com dedup por ``arquivo_origem``."""

    def __init__(self, path: str | Path, columns: tuple[str, ...] = MANIFEST_COLUMNS) -> None:
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
                rel = (row.get("arquivo_origem") or "").strip()
                if rel:
                    self._seen.add(rel)

    def __enter__(self) -> FormattedManifest:
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

    def __len__(self) -> int:
        return len(self._seen)

    def already_formatted(self, rel: str) -> bool:
        return rel in self._seen

    def mark(self, rel: str, engine: str, caracteres: int) -> bool:
        """Registra ``rel`` como formatado. ``False`` se já constava (dedup)."""
        if self._fh is None:
            raise RuntimeError("FormattedManifest usado fora do bloco 'with'.")
        if rel in self._seen:
            return False
        values = {
            "arquivo_origem": rel,
            "engine": engine,
            "caracteres": caracteres,
            "formatado_em": datetime.now().isoformat(timespec="seconds"),
        }
        self._writer.writerow([values[col] for col in self.columns])
        self._fh.flush()  # progresso em disco (sobrevive a interrupção)
        self._seen.add(rel)
        return True


def is_pending(manifest: FormattedManifest, rel: str, dest: Path) -> bool:
    """Um alvo continua pendente se não consta no manifesto **ou** perdeu o ``.txt``.

    A checagem do ``.txt`` cobre o caso de alguém apagar a saída: o registro
    sozinho daria o documento por pronto para sempre.
    """
    if not manifest.already_formatted(rel):
        return True
    return not (dest.exists() and dest.stat().st_size > 0)
