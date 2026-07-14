"""Validação de conteúdo e detecção de expiração (E-05/E-04)."""

from superlogica_file_downloader.content import (
    detect_expiration,
    is_html,
    looks_like_pdf,
    validate_content,
)

_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\n"
_HTML_LOGIN = b"<html><head></head><body>Login: accesskey expirado</body></html>"


def test_looks_like_pdf_true():
    assert looks_like_pdf(_PDF) is True


def test_looks_like_pdf_false_for_html():
    assert looks_like_pdf(_HTML_LOGIN) is False


def test_is_html_by_content_type():
    assert is_html(b"qualquer coisa", "text/html; charset=utf-8") is True


def test_validate_content_accepts_pdf():
    ok, motivo = validate_content(_PDF, "application/pdf")
    assert ok is True
    assert motivo == ""


def test_validate_content_rejects_html_error_page():
    ok, motivo = validate_content(_HTML_LOGIN, "text/html")
    assert ok is False
    assert "HTML" in motivo


def test_validate_content_rejects_unknown_binary():
    ok, motivo = validate_content(b"\x00\x01\x02not a pdf", "application/octet-stream")
    assert ok is False
    assert "não-PDF" in motivo


def test_detect_expiration_on_forbidden_status():
    assert detect_expiration(403, "", b"") is True
    assert detect_expiration(410, "", b"") is True


def test_detect_expiration_on_html_login_page():
    assert detect_expiration(200, "text/html", _HTML_LOGIN) is True


def test_no_expiration_on_valid_pdf():
    assert detect_expiration(200, "application/pdf", _PDF) is False


def test_no_expiration_on_transient_server_error():
    assert detect_expiration(500, "", b"") is False
