"""Tests de parsing das âncoras (T011) e retry/backoff (T029) do Superlógica."""

import pathlib

import pytest

from superlogica_download_map.config import build_config
from superlogica_download_map.superlogica import (
    SuperlogicaError,
    fallback_filename,
    parse_download_anchors,
    resolve_hyperlink,
)

_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "superlogica_page.html"


@pytest.fixture
def html() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


# --- parsing (unit: sem rede/disco além da fixture já carregada) -------------


def test_captures_all_download_anchors_not_just_first(html):
    anchors = parse_download_anchors(html)
    assert len(anchors) == 3  # ignora a âncora de navegação


def test_extracts_href_and_decoded_title(html):
    anchors = parse_download_anchors(html)
    urls = [a[0] for a in anchors]
    names = [a[1] for a in anchors]
    assert "id=112235" in urls[0]
    assert names[0] == "img20260602_08372180.pdf"
    assert names[1] == "Recibo de Pagamento.pdf"  # URL-decoded (E-09)
    assert names[2] == ""  # sem title → vazio (fallback aplicado pelo pipeline)


def test_empty_html_returns_no_anchors():
    assert parse_download_anchors("") == []
    assert parse_download_anchors("<html><body>nada</body></html>") == []


def test_fallback_filename_from_supplier_and_url_id():
    url = "https://x/publico/downloadarquivo?id=112237&hash=deadbeef"
    assert (
        fallback_filename("SINGULAR ENGENHARIA E CONSTRUCAO LTDA", url)
        == "SINGULAR_ENGENHARIA_E_CONSTRUCAO_LTDA_112237.pdf"
    )


# --- retry / backoff ---------------------------------------------------------


class _Resp:
    def __init__(self, status_code: int, text: str = "", content_type: str = "text/html",
                 disposition: str = ""):
        self.status_code = status_code
        self.text = text
        self.headers = {}
        if content_type:
            self.headers["Content-Type"] = content_type
        if disposition:
            self.headers["Content-Disposition"] = disposition

    def close(self):
        pass


class _Session:
    """Session falsa: devolve respostas em sequência (ou levanta exceções)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, timeout=None, stream=False):
        item = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _cfg(tmp_path):
    return build_config(tmp_path)


def test_retries_then_succeeds(tmp_path):
    sess = _Session([_Resp(500), _Resp(200, "<html>ok</html>")])
    out = resolve_hyperlink("http://x", _cfg(tmp_path), session=sess, sleep=lambda *_: None)
    assert out.kind == "html"
    assert out.text == "<html>ok</html>"
    assert sess.calls == 2


def test_no_retry_on_404(tmp_path):
    sess = _Session([_Resp(404)])
    with pytest.raises(SuperlogicaError):
        resolve_hyperlink("http://x", _cfg(tmp_path), session=sess, sleep=lambda *_: None)
    assert sess.calls == 1  # 404 não é retentado


def test_exhausts_retries_on_429(tmp_path):
    sess = _Session([_Resp(429), _Resp(429), _Resp(429)])
    with pytest.raises(SuperlogicaError):
        resolve_hyperlink("http://x", _cfg(tmp_path), session=sess, sleep=lambda *_: None)
    assert sess.calls == 3  # http_retries padrão


def test_network_error_then_success(tmp_path):
    sess = _Session([RuntimeError("conexão caiu"), _Resp(200, "ok")])
    out = resolve_hyperlink("http://x", _cfg(tmp_path), session=sess, sleep=lambda *_: None)
    assert out.kind == "html"
    assert out.text == "ok"
    assert sess.calls == 2


def test_resolves_direct_pdf_with_real_filename(tmp_path):
    # Despesa de anexo único: o endpoint devolve o PDF direto (antes era falso E-05).
    sess = _Session(
        [_Resp(200, content_type="application/pdf",
               disposition='inline; filename="elevador avis.pdf"')]
    )
    out = resolve_hyperlink("http://x/arquivos?id=1", _cfg(tmp_path), session=sess,
                            sleep=lambda *_: None)
    assert out.kind == "file"
    assert out.url == "http://x/arquivos?id=1"
    assert out.filename == "elevador avis.pdf"
