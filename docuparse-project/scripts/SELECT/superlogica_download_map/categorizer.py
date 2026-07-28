"""Classificação de categoria → pasta de destino (Seção 5.2.1 e Seção 6).

- :func:`split_categoria_complemento` divide a célula "Categoria - Complemento"
  no primeiro ` - ` (RN-8).
- :func:`canonical_key` gera a chave canônica (minúscula, sem acento/pontuação).
- :func:`categorize` aplica: (A) chave canônica → (B) regras de família →
  (C) fallback Title Case; indeterminado → ``_A_Revisar``.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from superlogica_download_map.config import CATEGORY_SEP, FALLBACK_FOLDER, FAMILY_RULES
from superlogica_download_map.sanitize import sanitize

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")


def split_categoria_complemento(cell: str | None) -> tuple[str, str]:
    """Divide no **primeiro** ` - ` (espaço-hífen-espaço). RN-8 / Seção 5.2.1.

    Sem o separador → célula inteira é a categoria e complemento vazio.
    Com múltiplos ` - ` → divide só no primeiro; o resto vai para o complemento.
    """
    if not cell:
        return "", ""
    # Não fazer strip do todo antes: removeria o espaço final que faz parte
    # do separador " - " (ex.: "Limpeza - ").
    if CATEGORY_SEP in cell:
        categoria, complemento = cell.split(CATEGORY_SEP, 1)
        return categoria.strip(), complemento.strip()
    return cell.strip(), ""


def canonical_key(categoria: str) -> str:
    """Chave canônica: minúsculas, sem acento (Unicode→ASCII), sem pontuação."""
    if not categoria:
        return ""
    lowered = categoria.lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    spaced = _NON_ALNUM.sub(" ", no_accents)
    return _WS.sub(" ", spaced).strip()


def _title_case(text: str) -> str:
    return " ".join(word.capitalize() for word in text.split())


def categorize(
    categoria_bruta: str,
    *,
    family_rules: tuple[tuple[str, str], ...] = FAMILY_RULES,
) -> str:
    """Deriva a pasta de destino a partir da categoria (nunca da célula inteira).

    Determinística: variantes com a mesma chave canônica caem na mesma pasta;
    famílias agrupam via ``family_rules``; o resto vira pasta própria (Title
    Case); vazio/indeterminado → ``_A_Revisar`` (E-07).
    """
    key = canonical_key(categoria_bruta)
    if not key:
        return FALLBACK_FOLDER
    for pattern, folder in family_rules:
        if re.search(pattern, key):
            return folder
    derived = sanitize(categoria_bruta)
    if not derived or derived == sanitize(""):
        return FALLBACK_FOLDER
    return _title_case(derived)


def aggregate_categories(
    raw_cells: Iterable[str],
    *,
    family_rules: tuple[tuple[str, str], ...] = FAMILY_RULES,
) -> list[tuple[str, str, str]]:
    """Inventário da passada de reconhecimento (US5).

    A partir das células "Categoria - Complemento" brutas, isola a categoria,
    coleta as **distintas** e produz ``(categoria_bruta, chave_canonica,
    pasta_destino_proposta)`` ordenado, para revisão humana do dicionário.
    """
    seen: dict[str, tuple[str, str]] = {}
    for cell in raw_cells:
        categoria, _complemento = split_categoria_complemento(cell)
        if not categoria:
            continue
        seen[categoria] = (
            canonical_key(categoria),
            categorize(categoria, family_rules=family_rules),
        )
    return sorted((cat, key, folder) for cat, (key, folder) in seen.items())
