"""Validação do conteúdo baixado e detecção de expiração (E-05/E-04, research D2/D3).

Um ``200 OK`` não garante que veio um documento válido — ``accesskey`` expirado
costuma devolver HTML de erro/login. Validamos pela **assinatura de bytes**, com o
``Content-Type`` como sinal complementar. Além de PDF (``%PDF``), aceitamos os
formatos de **imagem** que o backend-ocr processa (comprovantes fotografados vêm
como JPEG/PNG): a Fase C extrai o texto deles via OCR igual faz com um scan. HTML
continua rejeitado (é página de erro, não documento). Funções puras, sem rede.
"""

from __future__ import annotations

_HTML_MARKERS = (b"<html", b"<!doctype", b"<head", b"<body")
# Marcadores textuais de página de sessão/expiração/login.
_EXPIRE_MARKERS = ("accesskey", "login", "expir", "sess", "acesso negado")

# Assinaturas de imagem aceitas (magic bytes), alinhadas às extensões que o
# backend-ocr processa (raw_text_maker.config.SOURCE_EXTENSIONS). WEBP é tratado à
# parte por ter a marca ``WEBP`` deslocada dentro do contêiner RIFF.
_IMAGE_SIGNATURES: tuple[bytes, ...] = (
    b"\xff\xd8\xff",          # JPEG
    b"\x89PNG\r\n\x1a\n",     # PNG
    b"II*\x00",               # TIFF little-endian
    b"MM\x00*",               # TIFF big-endian
    b"BM",                    # BMP
)


def looks_like_pdf(head: bytes, signature: bytes = b"%PDF") -> bool:
    return head[: len(signature)] == signature


def looks_like_image(head: bytes) -> bool:
    """Assinatura de um formato de imagem que o backend-ocr sabe processar."""
    if any(head.startswith(sig) for sig in _IMAGE_SIGNATURES):
        return True
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"  # WEBP


def is_html(head: bytes, content_type: str = "") -> bool:
    if "text/html" in (content_type or "").lower():
        return True
    low = head[:512].lower()
    return any(marker in low for marker in _HTML_MARKERS)


def validate_content(
    head: bytes,
    content_type: str,
    *,
    signature: bytes = b"%PDF",
    accept_images: bool = True,
) -> tuple[bool, str]:
    """``(ok, motivo)``. Aceita PDF e (opcionalmente) imagem; rejeita HTML (E-05)."""
    if looks_like_pdf(head, signature):
        return True, ""
    if accept_images and looks_like_image(head):
        return True, ""
    if is_html(head, content_type):
        return False, "conteúdo inválido (HTML, não-documento)"
    return False, "conteúdo inválido (assinatura não reconhecida)"


def detect_expiration(status_code: int, content_type: str, head: bytes) -> bool:
    """Padrão de provável expiração de ``accesskey``/``hash`` (E-04)."""
    if status_code in (401, 403, 410):
        return True
    if status_code == 200 and is_html(head, content_type):
        text = head[:2048].decode("latin-1", "ignore").lower()
        return any(marker in text for marker in _EXPIRE_MARKERS)
    return False
