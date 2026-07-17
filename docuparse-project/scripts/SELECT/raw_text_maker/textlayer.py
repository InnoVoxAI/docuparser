"""Sonda local de camada de texto (PyMuPDF) — a "porta de entrada" do modo formatado.

Decide, sem chamar o backend-ocr, se um documento tem texto digital extraível.
É o que separa os arquivos que rodam por docling (têm ``raw_text_formatted``) dos
scans que caem no openrouter — e evita reenviar os scans, que custariam ~25s de
openrouter cada (ver ``backend-ocr/application/process_document.py:169-194``: o
fallback por texto vazio dispara mesmo com o engine forçado).

É só uma heurística de custo: a decisão final de sobrescrever fica no pipeline,
que só grava quando o backend devolve formatado não-vazio de fato.

Importa ``pymupdf`` diretamente de propósito: o pacote ``fitz`` instalado no venv
é um stub quebrado que sombreia o PyMuPDF real.
"""

from __future__ import annotations

from pathlib import Path


class PyMuPDFUnavailable(RuntimeError):
    """PyMuPDF não importável — sem ele não dá para gatear o modo formatado."""


def ensure_available() -> None:
    """Preflight: garante que a sonda funciona antes de qualquer trabalho.

    Sem PyMuPDF não há como decidir localmente o que enviar; abortar cedo é
    melhor que reenviar os 45 scans ao openrouter em silêncio.
    """
    try:
        import pymupdf  # noqa: F401
    except ImportError as exc:  # pragma: no cover - ambiente sem a lib
        raise PyMuPDFUnavailable(
            "modo --formatted precisa do PyMuPDF (pacote 'pymupdf'). "
            "Instale-o no ambiente do script."
        ) from exc


def has_text_layer(path: Path, min_chars: int) -> bool:
    """``True`` se ``path`` tem ao menos ``min_chars`` de texto digital extraível.

    Não-PDF (imagens) é sempre scan → ``False``. Um PDF ilegível aqui devolve
    ``True`` (não descarta: deixa o backend tentar; a regra de sobrescrita
    protege contra gravar lixo).
    """
    if path.suffix.lower() != ".pdf":
        return False

    import pymupdf

    # Silencia os avisos de sintaxe do MuPDF (ex.: "cannot find ExtGState") — são
    # ruído em PDFs tortos e não impedem a extração de texto.
    pymupdf.TOOLS.mupdf_display_errors(False)

    try:
        with pymupdf.open(path) as doc:
            chars = 0
            for page in doc:
                chars += len(page.get_text("text").strip())
                if chars >= min_chars:
                    return True
    except Exception:
        return True
    return False
