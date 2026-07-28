"""Salto 2 — resolução da página pública do Superlógica e raspagem das âncoras.

- :func:`resolve_hyperlink` faz GET com retry/backoff (E-10) e **distingue** dois
  formatos de resposta: uma **galeria HTML** (para raspar âncoras) ou **o PDF
  direto** (despesa de anexo único, que o endpoint entrega como
  ``application/pdf``). Sem isso, o PDF direto virava um falso E-05.
- :func:`parse_download_anchors` extrai, de **cada** âncora de download, o
  ``href`` e o nome real (``title`` do ``<img>``), com URL-decode (E-09).
- :func:`fallback_filename` gera o nome determinístico quando o ``title`` falta
  (E-06): ``{fornecedor_sanitizado}_{id_da_url}.pdf``.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from superlogica_download_map.sanitize import sanitize, url_decode

if TYPE_CHECKING:
    from superlogica_download_map.config import Config

_DOWNLOAD_MARKER = "downloadarquivo"
# Erros HTTP que não adianta repetir (link quebrado / accesskey expirado).
_NO_RETRY_STATUS = {400, 401, 403, 404, 410}
# Extrai o nome do arquivo de um cabeçalho Content-Disposition.
_CONTENT_DISPOSITION = re.compile(r'filename\*?=(?:"([^"]+)"|([^;]+))', re.IGNORECASE)


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


@dataclass
class Resolved:
    """Como um hyperlink resolveu: galeria HTML (raspar) ou PDF direto (baixar).

    O endpoint ``publico/arquivos?accesskey=...`` ora devolve uma página HTML com
    ícones de download, ora **o próprio PDF** (despesa de anexo único). Distinguir
    os dois evita perder os arquivos diretos (antes registrados como E-05).
    """

    kind: str  # "html" | "file"
    text: str = ""  # corpo HTML (kind == "html")
    url: str = ""  # URL que serve o arquivo (kind == "file")
    filename: str = ""  # nome real via Content-Disposition (kind == "file")


def _header(resp, name: str) -> str:
    headers = getattr(resp, "headers", None) or {}
    return headers.get(name) or ""


def _safe_close(resp) -> None:
    close = getattr(resp, "close", None)
    if callable(close):
        close()


def _filename_from_disposition(header: str) -> str:
    """Extrai ``filename`` de um ``Content-Disposition`` (URL-decoded, E-09)."""
    match = _CONTENT_DISPOSITION.search(header or "")
    if not match:
        return ""
    return url_decode((match.group(1) or match.group(2) or "").strip())


def _get_with_retry(url: str, config: Config, *, session, sleep: Callable[[float], None]):
    """GET com retry/backoff (E-10). Devolve a resposta 200; falha final → SuperlogicaError."""
    import requests

    sess = session or requests.Session()
    last_error = "desconhecido"
    for attempt in range(1, config.http_retries + 1):
        try:
            resp = sess.get(url, timeout=config.http_timeout_s, stream=True)
        except Exception as exc:  # noqa: BLE001 — inclui requests.RequestException
            last_error = str(exc)
        else:
            if resp.status_code == 200:
                return resp
            last_error = f"HTTP {resp.status_code}"
            _safe_close(resp)
            if resp.status_code in _NO_RETRY_STATUS:
                raise SuperlogicaError(f"{last_error} em {url}")
        if attempt < config.http_retries:
            sleep(config.http_backoff_base_s * attempt)  # backoff progressivo
    raise SuperlogicaError(f"falha após {config.http_retries} tentativas: {last_error}")


def resolve_hyperlink(
    url: str,
    config: Config,
    *,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
) -> Resolved:
    """Resolve a página de arquivos: galeria HTML (raspar) ou PDF direto (baixar).

    Distingue pelo ``Content-Type``: ``application/pdf`` → arquivo direto (usa o
    nome do ``Content-Disposition``); caso contrário lê o HTML para raspagem. Como
    reforço, um corpo que começa com ``%PDF`` também é tratado como arquivo.
    """
    resp = _get_with_retry(url, config, session=session, sleep=sleep)
    ctype = _header(resp, "Content-Type").lower()
    disposition = _header(resp, "Content-Disposition")
    if "application/pdf" in ctype:
        _safe_close(resp)
        return Resolved(kind="file", url=url, filename=_filename_from_disposition(disposition))
    text = resp.text
    _safe_close(resp)
    if text[:4] == "%PDF":  # content-type textual, mas o corpo é PDF (defensivo)
        return Resolved(kind="file", url=url, filename=_filename_from_disposition(disposition))
    return Resolved(kind="html", text=text)
