"""Configuração parametrizável do raw_text_maker.

Política de rede, extensões aceitas e colunas de saída ficam aqui, no topo —
nunca espalhadas na lógica. Os caminhos são resolvidos a partir do
``--source-root`` (a árvore de categorias produzida pela Fase B).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# --- Política de HTTP com o backend-ocr -------------------------------------
# O timeout espelha o OCRClient do backend-core (documents/services/ocr_client.py):
# um scan cai no fallback openrouter e leva dezenas de segundos, bem acima do
# timeout de 30s usado para downloads simples.
OCR_TIMEOUT_S = 300.0
OCR_RETRIES = 3
OCR_BACKOFF_BASE_S = 2.0
OCR_PAUSE_S = 0.0

# Mesma env var que o backend-core usa; no host o serviço está publicado em 8080.
BACKEND_OCR_URL_DEFAULT = os.getenv("BACKEND_OCR_URL", "http://localhost:8080")

# --- Árvore de saída --------------------------------------------------------
SOURCE_ROOT_DEFAULT = Path("downloads/fases/downloads")
OUTPUT_DIR_NAME = "Raw Text Docs"
ERRORS_FILE_NAME = "raw_text_erros.csv"
# Registro do que já foi formatado (gate de pendentes do modo --formatted).
MANIFEST_FILE_NAME = "raw_text_formatted.csv"

# --- Modo --formatted (texto com layout espacial) ---------------------------
# Mínimo de caracteres extraíveis (PyMuPDF) para considerar que um PDF tem
# camada de texto digital — ou seja, que roteia para o docling e tem
# raw_text_formatted. Abaixo disso é tratado como scan (rota openrouter) e não é
# reenviado: só uma sonda de custo, não classificação definitiva (a regra de
# sobrescrita no pipeline é quem garante a correção).
TEXT_LAYER_MIN_CHARS = 20

# Extensões que o backend-ocr processa (PDF ou imagem). Qualquer outra coisa na
# árvore (ex.: ``.part`` interrompido da Fase B, ``.csv``) é ignorada em vez de
# virar erro — não é documento.
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
)

TEXT_SUFFIX = ".txt"

# --- Colunas do relatório de erros ------------------------------------------
ERROR_COLUMNS: tuple[str, ...] = (
    "arquivo_origem",
    "categoria",
    "motivo",
    "tentativas",
    "ocorrido_em",
)

# --- Colunas do manifesto de formatados -------------------------------------
MANIFEST_COLUMNS: tuple[str, ...] = (
    "arquivo_origem",
    "engine",
    "caracteres",
    "formatado_em",
)


@dataclass(frozen=True)
class Config:
    """Configuração resolvida para uma execução."""

    source_root: Path
    output_root: Path
    errors_path: Path
    manifest_path: Path
    ocr_url: str = BACKEND_OCR_URL_DEFAULT
    ocr_timeout_s: float = OCR_TIMEOUT_S
    ocr_retries: int = OCR_RETRIES
    ocr_backoff_base_s: float = OCR_BACKOFF_BASE_S
    ocr_pause_s: float = OCR_PAUSE_S
    engine: str | None = None
    formatted: bool = False
    reformat_all: bool = False
    text_layer_min_chars: int = TEXT_LAYER_MIN_CHARS


def build_config(
    source_root: str | Path | None = None,
    *,
    output_root: str | Path | None = None,
    errors_path: str | Path | None = None,
    ocr_url: str | None = None,
    timeout: float | None = None,
    retries: int | None = None,
    pause: float | None = None,
    engine: str | None = None,
    formatted: bool = False,
    reformat_all: bool = False,
    manifest_path: str | Path | None = None,
) -> Config:
    """Constrói a configuração; saídas ficam ao lado da árvore de origem.

    Por padrão ``Raw Text Docs/``, o CSV de erros e o manifesto de formatados são
    irmãos de ``downloads/`` (ou seja, dentro de ``downloads/fases/``), o que
    mantém a pasta de saída contendo **apenas** as subpastas de categoria e seus
    ``.txt``.

    No modo ``formatted``, força o engine docling quando o chamador não escolheu
    um: só o docling produz ``raw_text_formatted``, e o objetivo é justamente
    (re)gerar o formatado dos documentos que já rodam por ele.
    """
    src = Path(source_root or SOURCE_ROOT_DEFAULT).resolve()
    out = Path(output_root).resolve() if output_root else src.parent / OUTPUT_DIR_NAME
    return Config(
        source_root=src,
        output_root=out,
        errors_path=(Path(errors_path).resolve() if errors_path else out.parent / ERRORS_FILE_NAME),
        manifest_path=(
            Path(manifest_path).resolve()
            if manifest_path
            else out.parent / MANIFEST_FILE_NAME
        ),
        ocr_url=(ocr_url or BACKEND_OCR_URL_DEFAULT).rstrip("/"),
        ocr_timeout_s=timeout if timeout is not None else OCR_TIMEOUT_S,
        ocr_retries=retries if retries is not None else OCR_RETRIES,
        ocr_pause_s=pause if pause is not None else OCR_PAUSE_S,
        engine=engine or ("docling" if formatted else None),
        formatted=formatted,
        reformat_all=reformat_all,
    )
