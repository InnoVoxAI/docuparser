"""Salto 3 — GET público na ``url_download`` com resiliência (E-02/E-03/E-09/E-10).

- Sessão reutilizada, ``timeout`` por requisição, retry com backoff progressivo.
- Status não-repetíveis (``{400,401,403,404,410}``) abortam cedo (não adianta
  repetir link quebrado / accesskey expirado).
- Valida o conteúdo (assinatura ``%PDF``) e sinaliza **provável expiração** (E-04).
- ``sleep`` é injetável para testar o backoff sem dormir.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from superlogica_file_downloader.content import detect_expiration, validate_content

if TYPE_CHECKING:
    from superlogica_file_downloader.config import Config

# Erros HTTP que não adianta repetir.
_NO_RETRY_STATUS = {400, 401, 403, 404, 410}
_HEAD_BYTES = 1024


@dataclass
class DownloadOutcome:
    """Resultado de baixar uma linha (data-model §3)."""

    ok: bool
    content: bytes | None = None
    motivo: str = ""
    tentativas: int = 0
    possivel_expiracao: bool = False


def _valid_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def download_file(
    url: str,
    config: Config,
    *,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
) -> DownloadOutcome:
    """GET com retry/backoff. Sucesso → bytes validados; falha → motivo + tentativas."""
    if not _valid_url(url):
        return DownloadOutcome(False, motivo="url malformada", tentativas=0)  # E-02

    sess = session or _new_session()
    last = "desconhecido"
    tentativas = 0
    for attempt in range(1, config.http_retries + 1):
        tentativas = attempt
        outcome, retry, last = _attempt(sess, url, config, tentativas)
        if outcome is not None:
            return outcome
        if retry and attempt < config.http_retries:
            sleep(config.http_backoff_base_s * attempt)  # backoff progressivo
    return DownloadOutcome(False, motivo=f"falha após {tentativas} tentativas: {last}",
                           tentativas=tentativas)


def _attempt(
    sess, url: str, config: Config, tentativas: int
) -> tuple[DownloadOutcome | None, bool, str]:
    """Uma tentativa. Retorna ``(resultado_definitivo|None, deve_repetir, ultimo_erro)``."""
    try:
        resp = sess.get(url, timeout=config.http_timeout_s, stream=True)
    except Exception as exc:  # noqa: BLE001 — inclui requests.RequestException / conexão caída
        return None, True, f"conexão: {exc}"

    status = resp.status_code
    content = resp.content
    ctype = resp.headers.get("Content-Type", "")
    head = content[:_HEAD_BYTES] if content else b""

    if status == 200:
        ok, motivo = validate_content(
            head, ctype, signature=config.pdf_signature, accept_images=config.accept_images
        )
        if ok:
            return DownloadOutcome(True, content=content, tentativas=tentativas), False, ""
        # Conteúdo estável e inválido: não repetir; pode ser expiração (E-05/E-04).
        exp = detect_expiration(status, ctype, head)
        return DownloadOutcome(False, motivo=motivo, tentativas=tentativas,
                               possivel_expiracao=exp), False, motivo

    last = f"HTTP {status}"
    if status in _NO_RETRY_STATUS:
        exp = detect_expiration(status, ctype, head)
        return DownloadOutcome(False, motivo=last, tentativas=tentativas,
                               possivel_expiracao=exp), False, last
    return None, True, last  # 5xx e afins → repetir


def _new_session():
    import requests

    return requests.Session()
