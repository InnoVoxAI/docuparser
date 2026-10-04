"""Validação de CNPJ (inclusive alfanumérico) e CPF."""

from __future__ import annotations

import re

_PUNCTUATION = re.compile(r"[\s./-]")
_CNPJ_FORMAT = re.compile(r"[0-9A-Z]{12}[0-9]{2}")
_CNPJ_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CPF_FORMAT = re.compile(r"[0-9]{11}")


def normalize_tax_id(value: str) -> str:
    """Remove a pontuação; o CNPJ alfanumérico fica em maiúsculas."""
    return _PUNCTUATION.sub("", value).upper()


def _cnpj_check_digit(base: str) -> str:
    weights = _CNPJ_WEIGHTS[-len(base) :]
    total = sum((ord(char) - 48) * weight for char, weight in zip(base, weights))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def is_valid_cnpj(cnpj: str) -> bool:
    """Valida formato e dígitos verificadores, inclusive do CNPJ alfanumérico."""
    if not _CNPJ_FORMAT.fullmatch(cnpj) or len(set(cnpj)) == 1:
        return False
    first = _cnpj_check_digit(cnpj[:12])
    return cnpj[12:] == first + _cnpj_check_digit(cnpj[:12] + first)


def _cpf_check_digit(base: str) -> str:
    total = sum(
        int(digit) * weight for digit, weight in zip(base, range(len(base) + 1, 1, -1))
    )
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def is_valid_cpf(cpf: str) -> bool:
    if not _CPF_FORMAT.fullmatch(cpf) or len(set(cpf)) == 1:
        return False
    first = _cpf_check_digit(cpf[:9])
    return cpf[9:] == first + _cpf_check_digit(cpf[:9] + first)


def is_valid_tax_id(value: str) -> bool:
    return is_valid_cpf(value) or is_valid_cnpj(value)
