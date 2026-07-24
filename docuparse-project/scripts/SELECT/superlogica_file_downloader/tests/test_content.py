"""Validação de conteúdo e detecção de expiração (E-05/E-04)."""

import pytest
from superlogica_file_downloader.content import (
    detect_expiration,
    is_html,
    looks_like_image,
    looks_like_pdf,
    validate_content,
)

_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\n"
_HTML_LOGIN = b"<html><head></head><body>Login: accesskey expirado</body></html>"
_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 20
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
_TIFF = b"II*\x00" + b"\x00" * 20
_BMP = b"BM" + b"\x00" * 20
_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 12


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
    assert "não reconhecida" in motivo


@pytest.mark.parametrize("head", [_JPEG, _PNG, _TIFF, _BMP, _WEBP])
def test_looks_like_image_true_for_supported_formats(head):
    assert looks_like_image(head) is True


def test_looks_like_image_false_for_pdf_and_html():
    assert looks_like_image(_PDF) is False
    assert looks_like_image(_HTML_LOGIN) is False


@pytest.mark.parametrize("head", [_JPEG, _PNG, _TIFF, _BMP, _WEBP])
def test_validate_content_accepts_images_by_default(head):
    ok, motivo = validate_content(head, "image/jpeg")
    assert ok is True
    assert motivo == ""


def test_validate_content_rejects_images_when_pdf_only():
    ok, motivo = validate_content(_JPEG, "image/jpeg", accept_images=False)
    assert ok is False
    assert "não reconhecida" in motivo


def test_validate_content_still_rejects_html_even_with_images_on():
    ok, motivo = validate_content(_HTML_LOGIN, "text/html", accept_images=True)
    assert ok is False
    assert "HTML" in motivo


def test_detect_expiration_on_forbidden_status():
    assert detect_expiration(403, "", b"") is True
    assert detect_expiration(410, "", b"") is True


def test_detect_expiration_on_html_login_page():
    assert detect_expiration(200, "text/html", _HTML_LOGIN) is True


def test_no_expiration_on_valid_pdf():
    assert detect_expiration(200, "application/pdf", _PDF) is False


def test_no_expiration_on_transient_server_error():
    assert detect_expiration(500, "", b"") is False
