"""Validação do conteúdo baixado e detecção de expiração (E-05/E-04, research D2/D3).

Um ``200 OK`` não garante que veio um PDF — ``accesskey`` expirado costuma
devolver HTML de erro/login. Validamos pela **assinatura de bytes** (``%PDF``),
com o ``Content-Type`` como sinal complementar. Funções puras, testáveis sem rede.
"""

from __future__ import annotations

_HTML_MARKERS = (b"<html", b"<!doctype", b"<head", b"<body")
# Marcadores textuais de página de sessão/expiração/login.
_EXPIRE_MARKERS = ("accesskey", "login", "expir", "sess", "acesso negado")


def looks_like_pdf(head: bytes, signature: bytes = b"%PDF") -> bool:
    return head[: len(signature)] == signature


def is_html(head: bytes, content_type: str = "") -> bool:
    if "text/html" in (content_type or "").lower():
        return True
    low = head[:512].lower()
    return any(marker in low for marker in _HTML_MARKERS)


def validate_content(
    head: bytes, content_type: str, *, signature: bytes = b"%PDF"
) -> tuple[bool, str]:
    """``(ok, motivo)``. Rejeita HTML de erro e qualquer conteúdo não-PDF (E-05)."""
    if looks_like_pdf(head, signature):
        return True, ""
    if is_html(head, content_type):
        return False, "conteúdo inválido (HTML, não-PDF)"
    return False, "conteúdo inválido (assinatura não-PDF)"


def detect_expiration(status_code: int, content_type: str, head: bytes) -> bool:
    """Padrão de provável expiração de ``accesskey``/``hash`` (E-04)."""
    if status_code in (401, 403, 410):
        return True
    if status_code == 200 and is_html(head, content_type):
        text = head[:2048].decode("latin-1", "ignore").lower()
        return any(marker in text for marker in _EXPIRE_MARKERS)
    return False
