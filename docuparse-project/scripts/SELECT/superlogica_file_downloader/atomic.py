"""Gravação atômica em disco (E-11, research D5).

Grava em ``<destino>.part`` no mesmo diretório e só então renomeia
(``os.replace``, atômico no mesmo filesystem) para o nome final. Uma interrupção
nunca deixa um arquivo com nome definitivo e conteúdo incompleto — a retomada
(RN-4) enxerga corretamente o que está concluído.
"""

from __future__ import annotations

import os
from pathlib import Path


def save_atomic(dest_path: str | Path, content: bytes) -> None:
    """Grava ``content`` em ``<dest>.part`` e promove ao nome final via rename."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with open(tmp, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)  # atômico: só agora o nome final existe
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
