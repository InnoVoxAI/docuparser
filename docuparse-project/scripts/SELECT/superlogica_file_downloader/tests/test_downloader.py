"""Download básico (US1) e URL malformada (E-02)."""

from superlogica_file_downloader.config import build_config
from superlogica_file_downloader.downloader import download_file

_PDF = b"%PDF-1.7\ncorpo do pdf\n"
_URL = "https://admin.superlogica.net/publico/downloadarquivo?id=1&hash=h"


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls: list[str] = []

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        self.calls.append(url)
        return self.response


def _noop(_seconds):
    pass


def test_successful_download_returns_validated_bytes(tmp_path):
    config = build_config(tmp_path)
    session = FakeSession(FakeResponse(200, _PDF, {"Content-Type": "application/pdf"}))
    outcome = download_file(_URL, config, session=session, sleep=_noop)
    assert outcome.ok is True
    assert outcome.content == _PDF
    assert session.calls == [_URL]


def test_malformed_url_fails_without_request(tmp_path):
    config = build_config(tmp_path)
    session = FakeSession(FakeResponse(200, _PDF))
    outcome = download_file("", config, session=session, sleep=_noop)
    assert outcome.ok is False
    assert "malformada" in outcome.motivo
    assert session.calls == []  # nem tentou (E-02)


def test_html_error_page_is_rejected(tmp_path):
    config = build_config(tmp_path)
    html = b"<html><body>accesskey expirado</body></html>"
    session = FakeSession(FakeResponse(200, html, {"Content-Type": "text/html"}))
    outcome = download_file(_URL, config, session=session, sleep=_noop)
    assert outcome.ok is False
    assert outcome.possivel_expiracao is True  # E-04
