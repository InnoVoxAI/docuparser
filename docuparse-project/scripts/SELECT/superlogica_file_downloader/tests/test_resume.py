"""Retomada idempotente + fail-soft de ponta a ponta (RN-4/RN-6/E-12)."""

import csv

from superlogica_file_downloader.config import build_config
from superlogica_file_downloader.map_io import MAP_COLUMNS, load_map
from superlogica_file_downloader.pipeline import run

_PDF = b"%PDF-1.7\ncorpo\n"
_URL_OK = "https://x/publico/downloadarquivo?id=1&hash=h"
_URL_BAD = "https://x/publico/downloadarquivo?id=2&hash=h"


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class RoutingSession:
    """Responde por URL e registra as chamadas."""

    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        self.calls.append(url)
        if url == _URL_OK:
            return FakeResponse(200, _PDF, {"Content-Type": "application/pdf"})
        return FakeResponse(404)


def _noop(_seconds):
    pass


def _write_map(path):
    rows = [
        {"url_download": _URL_OK, "nome_arquivo": "a.pdf", "pasta_destino": "Água",
         "categoria_bruta": "Água", "hyperlink_origem": "https://x/arquivos?accesskey=k",
         "pdf_origem": "d.pdf", "status": "pendente", "fornecedor": "F", "complemento": ""},
        {"url_download": _URL_BAD, "nome_arquivo": "b.pdf", "pasta_destino": "Água",
         "categoria_bruta": "Água", "hyperlink_origem": "https://x/arquivos?accesskey=k",
         "pdf_origem": "d.pdf", "status": "pendente", "fornecedor": "F", "complemento": ""},
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in MAP_COLUMNS})


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_first_run_downloads_ok_and_records_error(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    session = RoutingSession()

    summary = run(config, session=session, sleep=_noop)

    assert summary["baixados"] == 1
    assert summary["erros"] == 1
    assert (config.downloads_root / "Água" / "a.pdf").exists()
    assert not (config.downloads_root / "Água" / "b.pdf").exists()

    final = _read(config.final_csv_path)
    assert [r["nome_arquivo"] for r in final] == ["a.pdf"]

    statuses = {r.url_download: r.status for r in load_map(config.map_path)}
    assert statuses[_URL_OK] == "baixado"
    assert statuses[_URL_BAD] == "erro"


def test_rerun_skips_done_and_retries_error_without_duplicating(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    run(config, session=RoutingSession(), sleep=_noop)

    # Reexecução: a linha concluída não é rebaixada; a que falhou é re-tentada.
    session2 = RoutingSession()
    summary2 = run(config, session=session2, sleep=_noop)

    assert _URL_OK not in session2.calls  # pulada (status baixado + arquivo presente)
    assert _URL_BAD in session2.calls      # re-tentada
    assert summary2["pulados"] == 1

    final = _read(config.final_csv_path)
    assert [r["nome_arquivo"] for r in final] == ["a.pdf"]  # sem duplicata (RN-6)


class ExpiredSession:
    """Sempre responde 403 (accesskey expirado)."""

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        return FakeResponse(403)


def test_expiration_is_flagged_in_summary_and_error_report(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)

    summary = run(config, session=ExpiredSession(), sleep=_noop)

    assert summary["expiracao"] >= 1  # sinal E-04 no resumo
    erros = _read(config.errors_path)
    assert any(r["possivel_expiracao"] == "sim" for r in erros)


def test_rerun_redownloads_when_file_missing(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    run(config, session=RoutingSession(), sleep=_noop)

    # status=baixado mas o arquivo sumiu do disco → deve rebaixar.
    (config.downloads_root / "Água" / "a.pdf").unlink()
    session2 = RoutingSession()
    run(config, session=session2, sleep=_noop)

    assert _URL_OK in session2.calls
    assert (config.downloads_root / "Água" / "a.pdf").exists()
