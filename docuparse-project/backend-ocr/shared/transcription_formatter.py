# =============================================================================
# SHARED: shared/transcription_formatter.py
# =============================================================================
# Formatador de transcrição independente de engine.
#
# Por que existe:
#   Apenas o DoclingEngine produz `raw_text_formatted` (layout espacial via
#   coordenadas de palavras do PDF digital). Para os demais engines — em
#   especial o OpenRouter/LLM em PDFs-imagem e imagens escaneadas — não há
#   coordenadas disponíveis, então a "Transcrição Formatada" ficava vazia.
#
#   Este módulo garante um único ponto de geração da transcrição formatada a
#   partir do `raw_text` já extraído: normaliza espaços e quebras de linha,
#   preservando a ordem de leitura. Não reconstrói tabelas (isso exigiria
#   coordenadas ou uma chamada extra ao LLM — fora de escopo por custo).
#
# Uso:
#   application/process_document.py chama format_transcription() como fallback
#   quando o engine não produziu `raw_text_formatted`.
# =============================================================================

from __future__ import annotations

import re

# Colapsa 3+ quebras de linha consecutivas em no máximo uma linha em branco.
_EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")

# Espaços/tabs à direita de cada linha.
_TRAILING_WHITESPACE = re.compile(r"[ \t]+(?=\n)")

# Sequências de espaços/tabs internos (2+) colapsadas em um único espaço.
_INNER_WHITESPACE = re.compile(r"[ \t]{2,}")


def format_transcription(raw_text: str) -> str:
    """
    Deriva uma transcrição formatada a partir do texto bruto do OCR.

    Formatação leve, preservando a ordem de leitura:
      - normaliza terminadores de linha (\\r\\n, \\r → \\n);
      - colapsa espaços/tabs internos repetidos em um único espaço;
      - remove espaços em branco no fim de cada linha;
      - colapsa 3+ quebras de linha em uma única linha em branco.

    Não tenta reconstruir o layout espacial (colunas/tabelas): para documentos
    baseados em imagem não há coordenadas, então o resultado é essencialmente
    o `raw_text` normalizado.

    Args:
        raw_text: Texto bruto extraído pelo engine OCR.

    Returns:
        Texto formatado (pode ser igual ao raw_text normalizado). String vazia
        se a entrada for vazia ou só espaços.
    """
    if not raw_text or not raw_text.strip():
        return ""

    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _INNER_WHITESPACE.sub(" ", normalized)
    normalized = _TRAILING_WHITESPACE.sub("", normalized)
    normalized = _EXCESSIVE_BLANK_LINES.sub("\n\n", normalized)

    return normalized.strip()
