"""Unit tests da divisão categoria/complemento (T018, RN-8). Sem rede/disco."""

import pytest

from superlogica_download_map.categorizer import split_categoria_complemento

pytestmark = pytest.mark.unit


def test_split_basic():
    cell = "Construção-Reformas - IMPERMEABILIZAÇÃO DE RESERVATÓRIOS PARC 10/10"
    categoria, complemento = split_categoria_complemento(cell)
    assert categoria == "Construção-Reformas"
    assert complemento == "IMPERMEABILIZAÇÃO DE RESERVATÓRIOS PARC 10/10"


def test_category_with_hyphen_without_spaces_is_not_split():
    # O separador é estritamente " - " (com espaços); hífen simples não divide.
    categoria, complemento = split_categoria_complemento("Construção-Reformas")
    assert categoria == "Construção-Reformas"
    assert complemento == ""


def test_no_separator_whole_is_category():
    categoria, complemento = split_categoria_complemento("Água")
    assert categoria == "Água"
    assert complemento == ""


def test_multiple_separators_split_only_first():
    categoria, complemento = split_categoria_complemento("A - B - C")
    assert categoria == "A"
    assert complemento == "B - C"


def test_strips_both_parts():
    categoria, complemento = split_categoria_complemento("  Energia   -   Conta de luz  ")
    assert categoria == "Energia"
    assert complemento == "Conta de luz"


def test_empty_and_none():
    assert split_categoria_complemento("") == ("", "")
    assert split_categoria_complemento(None) == ("", "")


def test_trailing_separator_gives_empty_complement():
    categoria, complemento = split_categoria_complemento("Limpeza - ")
    assert categoria == "Limpeza"
    assert complemento == ""
