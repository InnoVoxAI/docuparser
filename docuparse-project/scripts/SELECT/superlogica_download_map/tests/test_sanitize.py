"""Unit tests de sanitização (T007). Sem rede/disco."""

import pytest

from superlogica_download_map.sanitize import DEFAULT_FALLBACK, sanitize, url_decode

pytestmark = pytest.mark.unit


def test_url_decode_percent_and_plus():
    assert url_decode("BAHIANA+DISTRIBUIDORA") == "BAHIANA DISTRIBUIDORA"
    assert url_decode("IMPERMEABILIZA%C3%87%C3%83O") == "IMPERMEABILIZAÇÃO"
    assert url_decode("") == ""


def test_removes_invalid_filesystem_chars():
    assert sanitize('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"


def test_collapses_and_trims_whitespace():
    assert sanitize("  muitos   espaços \t aqui  ") == "muitos espaços aqui"


def test_strips_trailing_dot_and_space():
    assert sanitize("arquivo.  ") == "arquivo"


def test_preserves_accents():
    assert sanitize("Construção-Reformas") == "Construção-Reformas"


def test_empty_or_control_only_returns_fallback():
    assert sanitize("") == DEFAULT_FALLBACK
    assert sanitize(None) == DEFAULT_FALLBACK
    assert sanitize("\x00\x01\x02") == DEFAULT_FALLBACK


def test_reserved_windows_name_returns_fallback():
    assert sanitize("CON") == DEFAULT_FALLBACK
    assert sanitize("nul.txt") == DEFAULT_FALLBACK
    assert sanitize("COM1") == DEFAULT_FALLBACK


def test_custom_fallback():
    assert sanitize("", fallback="x.pdf") == "x.pdf"
