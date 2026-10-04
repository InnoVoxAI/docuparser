from __future__ import annotations

from condominiums.tax_ids import (
    is_valid_cnpj,
    is_valid_cpf,
    is_valid_tax_id,
    normalize_tax_id,
)


def test_normalize_strips_punctuation_and_uppercases() -> None:
    assert normalize_tax_id("12.abc.345/01de-35") == "12ABC34501DE35"
    assert normalize_tax_id("529.982.247-25") == "52998224725"


def test_cpf_check_digits() -> None:
    assert is_valid_cpf("52998224725")
    assert not is_valid_cpf("52998224726")
    assert not is_valid_cpf("11111111111")
    assert not is_valid_cpf("5299822472")


def test_tax_id_accepts_cpf_or_cnpj() -> None:
    assert is_valid_tax_id("52998224725")
    assert is_valid_tax_id("11222333000181")
    assert is_valid_cnpj("12ABC34501DE35")
    assert not is_valid_tax_id("11222333000182")
