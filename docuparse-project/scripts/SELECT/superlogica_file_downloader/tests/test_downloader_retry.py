"""Resiliência do download: retry/backoff e status não-repetíveis (E-03/E-10)."""

from superlogica_file_downloader.config import build_config
from superlogica_file_downloader.downloader import download_file

_PDF = b"%PDF-1.7\nok\n"
_URL = "https://x/publico/downloadarquivo?id=1&hash=h"
_PDF_HEADERS = {"Content-Type": "application/pdf"}


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class SequenceSession:
    """Devolve respostas em sequência; ``Exception`` é levantada (conexão caída)."""

    def __init__(self, items):
        self.items = list(items)
        self.calls = 0

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        item = self.items[min(self.calls, len(self.items) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _recording_sleep():
    waits: list[float] = []
    return waits, lambda s: waits.append(s)


def test_retries_then_succeeds(tmp_path):
    config = build_config(tmp_path, retries=3)
    session = SequenceSession(
        [FakeResponse(500), FakeResponse(500), FakeResponse(200, _PDF, _PDF_HEADERS)]
    )
    waits, sleep = _recording_sleep()
    outcome = download_file(_URL, config, session=session, sleep=sleep)
    assert outcome.ok is True
    assert outcome.tentativas == 3
    assert len(waits) == 2  # backoff entre as 3 tentativas


def test_no_retry_status_aborts_early(tmp_path):
    config = build_config(tmp_path, retries=3)
    session = SequenceSession([FakeResponse(404)])
    waits, sleep = _recording_sleep()
    outcome = download_file(_URL, config, session=session, sleep=sleep)
    assert outcome.ok is False
    assert outcome.tentativas == 1  # não repetiu
    assert "404" in outcome.motivo
    assert waits == []


def test_exhausts_retries_on_persistent_server_error(tmp_path):
    config = build_config(tmp_path, retries=3)
    session = SequenceSession([FakeResponse(503)])
    _waits, sleep = _recording_sleep()
    outcome = download_file(_URL, config, session=session, sleep=sleep)
    assert outcome.ok is False
    assert outcome.tentativas == 3
    assert "503" in outcome.motivo


def test_connection_error_is_retried(tmp_path):
    config = build_config(tmp_path, retries=2)
    session = SequenceSession([ConnectionError("caiu"), FakeResponse(200, _PDF, _PDF_HEADERS)])
    _waits, sleep = _recording_sleep()
    outcome = download_file(_URL, config, session=session, sleep=sleep)
    assert outcome.ok is True
    assert outcome.tentativas == 2
