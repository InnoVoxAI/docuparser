# =============================================================================
# SHARED: shared/validators.py
# =============================================================================
# Validações genéricas e reutilizáveis — sem dependência de domínio ou engine.
#
# Origem: extraído de utils/validate_fields.py (Fase 2 do refactor).
# A lógica original em validate_fields.py permanece intacta para backward compat.
# Na Fase 7, validate_fields.py será atualizado para importar daqui.
#
# O que há aqui:
#   - normalize_digits()      → strip para apenas dígitos
#   - validate_cnpj()         → checksum Módulo 11
#   - parse_currency_value()  → string BR → float (ex: "1.234,56" → 1234.56)
#   - is_valid_date_format()  → verifica padrão DD/MM/AAAA
#
# Regra: zero dependências internas — só stdlib.
# =============================================================================

from __future__ import annotations

import re
from typing import List


def normalize_digits(value: str) -> str:
    """Remove todos os caracteres não-numéricos. Útil para limpar CNPJ, CPF, CEP."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def validate_cnpj(cnpj: str | None) -> bool:
    """
    Valida CNPJ pelo algoritmo oficial (Módulo 11).

    Aceita os formatos:
      - "12.345.678/0001-90"  (formatado)
      - "12345678000190"       (apenas dígitos)

    Retorna False para CNPJ nulo, com comprimento errado ou sequências repetidas.
    """
    digits = normalize_digits(cnpj or "")
    if len(digits) != 14:
        return False

    # Sequências repetidas (00000000000000, 11111111111111, ...) são inválidas.
    if len(set(digits)) == 1:
        return False

    def _calc_digit(base: str, weights: List[int]) -> str:
        total = sum(int(num) * weight for num, weight in zip(base, weights))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return str(digit)

    first = _calc_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _calc_digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])

    return digits[-2:] == f"{first}{second}"


def parse_currency_value(value: str) -> float | None:
    """
    Converte string de moeda brasileira para float.

    Formatos aceitos:
      - "1.234,56"  → 1234.56
      - "1234,56"   → 1234.56
      - "R$ 1.234,56" → 1234.56
      - "1234.56"   → 1234.56  (formato americano — aceito como fallback)

    Retorna None para valor vazio, não-numérico ou zero.
    """
    if not value:
        return None

    # Remove símbolo de moeda e espaços.
    cleaned = re.sub(r"R\$", "", str(value), flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace(" ", "")

    if not cleaned:
        return None

    try:
        # Formato brasileiro: separador de milhar = ".", decimal = ","
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Formato americano ou inteiro: separador decimal = "." ou sem decimal
        result = float(cleaned)
        return result if result > 0 else None
    except (ValueError, TypeError):
        return None


def is_valid_date_format(value: str) -> bool:
    """
    Verifica se a string tem formato de data DD/MM/AAAA ou DD/MM/AA.

    Não valida se a data é calendaricamente real (ex: 31/02/2024) —
    apenas verifica o padrão de formatação.
    """
    if not value:
        return False

    pattern = r"^\d{2}/\d{2}/(\d{4}|\d{2})$"
    return bool(re.match(pattern, str(value).strip()))
