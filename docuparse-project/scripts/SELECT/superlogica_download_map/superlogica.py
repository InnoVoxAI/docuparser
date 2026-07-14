"""Salto 2 — resolução da página pública do Superlógica e raspagem das âncoras.

- :func:`fetch_page` faz GET com retry/backoff e pausa (E-10); falha final →
  :class:`SuperlogicaError` (tratada como E-04 pelo pipeline).
- :func:`parse_download_anchors` extrai, de **cada** âncora de download, o
  ``href`` e o nome real (``title`` do ``<img>``), com URL-decode (E-09).
- :func:`fallback_filename` gera o nome determinístico quando o ``title`` falta
  (E-06): ``{fornecedor_sanitizado}_{id_da_url}.pdf``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from superlogica_download_map.sanitize import sanitize, url_decode

if TYPE_CHECKING:
    from superlogica_download_map.config import Config

_DOWNLOAD_MARKER = "downloadarquivo"
# Erros HTTP que não adianta repetir (link quebrado / accesskey expirado).
_NO_RETRY_STATUS = {400, 401, 403, 404, 410}


class SuperlogicaError(RuntimeError):
    """Falha ao resolver a página de arquivos (E-04)."""


def parse_download_anchors(html: str) -> list[tuple[str, str]]:
    """Retorna ``[(url_download, nome_arquivo), ...]`` de todas as âncoras.

    ``nome_arquivo`` vem do ``title`` do ``<img>`` interno (URL-decoded); fica
    vazio quando ausente (o pipeline aplica o fallback E-06). Captura **todas**
    as âncoras de download da página (RN-1), nunca só a primeira.
    """
    soup = BeautifulSoup(html or "", "lxml")
    anchors: list[tuple[str, str]] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if _DOWNLOAD_MARKER not in href:
            continue
        img = tag.find("img")
        title = (img.get("title") or "").strip() if img else ""
        nome = url_decode(title) if title else ""
        anchors.append((href, nome))
    return anchors


def fallback_filename(fornecedor: str, url_download: str) -> str:
    """Nome determinístico quando o nome real está ausente (E-06)."""
    query = parse_qs(urlparse(url_download).query)
    file_id = (query.get("id") or ["arquivo"])[0]
    forn = sanitize(fornecedor, fallback="fornecedor").replace(" ", "_")
    return f"{forn}_{file_id}.pdf"


def fetch_page(
    url: str,
    config: Config,
    *,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """GET com retry/backoff (E-10). Sucesso → HTML; falha final → SuperlogicaError."""
    import requests

    sess = session or requests.Session()
    last_error = "desconhecido"
    for attempt in range(1, config.http_retries + 1):
        try:
            resp = sess.get(url, timeout=config.http_timeout_s)
        except Exception as exc:  # noqa: BLE001 — inclui requests.RequestException
            last_error = str(exc)
        else:
            if resp.status_code == 200:
                return resp.text
            last_error = f"HTTP {resp.status_code}"
            if resp.status_code in _NO_RETRY_STATUS:
                raise SuperlogicaError(f"{last_error} em {url}")
        if attempt < config.http_retries:
            sleep(config.http_backoff_base_s * attempt)  # backoff progressivo
    raise SuperlogicaError(f"falha após {config.http_retries} tentativas: {last_error}")
