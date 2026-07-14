"""Integração do pipeline completo (Drive + HTTP mockados). Valida US1–US4.

Não toca rede nem o Drive real: ``list_pdfs``/``download_pdf_bytes``/
``resolve_hyperlink`` são substituídos; a extração de PDF usa um PDF sintético e a
raspagem usa a fixture HTML real.
"""

import csv
import pathlib

import pymupdf
import pytest

from superlogica_download_map import pipeline
from superlogica_download_map.config import build_config
from superlogica_download_map.drive_reader import DrivePdf
from superlogica_download_map.superlogica import Resolved

_FIXTURE_HTML = (pathlib.Path(__file__).parent / "fixtures" / "superlogica_page.html").read_text(
    encoding="utf-8"
)


def _synthetic_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    for x, text in [(50, "Vencimento"), (150, "Fornecedor"), (300, "Categoria - Complemento"),
                    (500, "Compet."), (560, "Valor")]:
        page.insert_text((x, 100), text, fontsize=10)
    for x, text in [(50, "22/06/2026"), (150, "SINGULAR ENGENHARIA"),
                    (300, "Construção-Reformas - IMPERMEABILIZACAO"), (500, "06/2026"),
                    (560, "2.500,00")]:
        page.insert_text((x, 130), text, fontsize=10)
    page.insert_link(
        {"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(150, 122, 290, 135),
         "uri": "https://admin345902.superlogica.net/publico/arquivos?accesskey=xyz"}
    )
    return doc.tobytes()


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(pipeline, "list_pdfs", lambda *a, **k: [DrivePdf("id1", "despesas.pdf")])
    monkeypatch.setattr(pipeline, "download_pdf_bytes", lambda *a, **k: _synthetic_pdf())
    monkeypatch.setattr(
        pipeline, "resolve_hyperlink", lambda *a, **k: Resolved(kind="html", text=_FIXTURE_HTML)
    )


def _read_map(path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_run_full_produces_map_with_one_row_per_anchor(patched, tmp_path):
    config = build_config(tmp_path)
    summary = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert summary["arquivos"] == 3  # 3 âncoras na página → 3 linhas (RN-1)
    rows = _read_map(config.map_path)
    assert len(rows) == 3
    for row in rows:
        assert row["status"] == "pendente"
        assert row["categoria_bruta"] == "Construção-Reformas"
        assert row["complemento"] == "IMPERMEABILIZACAO"
        assert row["pasta_destino"] == "Construção-Reformas"
        assert row["pdf_origem"] == "despesas.pdf"
        assert "arquivos?accesskey=xyz" in row["hyperlink_origem"]


def test_run_full_applies_fallback_name_and_creates_folders(patched, tmp_path):
    config = build_config(tmp_path)
    pipeline.run_full(config, service=None, sleep=lambda *_: None)
    rows = _read_map(config.map_path)

    names = [r["nome_arquivo"] for r in rows]
    assert "img20260602_08372180.pdf" in names
    assert "Recibo de Pagamento.pdf" in names
    assert "SINGULAR_ENGENHARIA_112237.pdf" in names  # fallback E-06
    assert (config.downloads_root / "Construção-Reformas").is_dir()
    assert config.report_path.exists()


def test_run_full_is_idempotent_on_rerun(patched, tmp_path):
    config = build_config(tmp_path)
    pipeline.run_full(config, service=None, sleep=lambda *_: None)
    second = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert second["arquivos"] == 0  # nada novo gravado
    assert len(_read_map(config.map_path)) == 3  # sem duplicação


def _report_types(config):
    with config.report_path.open(encoding="utf-8") as fh:
        return [r["tipo"] for r in csv.DictReader(fh)]


def test_run_recon_writes_category_inventory(patched, tmp_path):
    config = build_config(tmp_path)
    summary = pipeline.run_recon(config, service=None)
    assert summary["categorias"] == 1
    with config.categories_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["categoria_bruta"] == "Construção-Reformas"
    assert rows[0]["pasta_destino_proposta"] == "Construção-Reformas"


def test_fail_soft_on_broken_superlogica_page(monkeypatch, tmp_path):
    from superlogica_download_map.superlogica import SuperlogicaError

    monkeypatch.setattr(pipeline, "list_pdfs", lambda *a, **k: [DrivePdf("id1", "despesas.pdf")])
    monkeypatch.setattr(pipeline, "download_pdf_bytes", lambda *a, **k: _synthetic_pdf())

    def _boom(*a, **k):
        raise SuperlogicaError("HTTP 404")

    monkeypatch.setattr(pipeline, "resolve_hyperlink", _boom)
    config = build_config(tmp_path)
    summary = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert summary["arquivos"] == 0
    assert _read_map(config.map_path) == []
    assert "E-04" in _report_types(config)


def test_fail_soft_on_page_without_anchors(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "list_pdfs", lambda *a, **k: [DrivePdf("id1", "despesas.pdf")])
    monkeypatch.setattr(pipeline, "download_pdf_bytes", lambda *a, **k: _synthetic_pdf())
    monkeypatch.setattr(
        pipeline,
        "resolve_hyperlink",
        lambda *a, **k: Resolved(kind="html", text="<html><body>vazio</body></html>"),
    )
    config = build_config(tmp_path)
    summary = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert summary["arquivos"] == 0
    assert "E-05" in _report_types(config)


def test_run_full_maps_direct_pdf_response(monkeypatch, tmp_path):
    # Despesa de anexo único: resolve_hyperlink devolve um arquivo direto, não galeria.
    monkeypatch.setattr(pipeline, "list_pdfs", lambda *a, **k: [DrivePdf("id1", "despesas.pdf")])
    monkeypatch.setattr(pipeline, "download_pdf_bytes", lambda *a, **k: _synthetic_pdf())
    monkeypatch.setattr(
        pipeline,
        "resolve_hyperlink",
        lambda *a, **k: Resolved(
            kind="file",
            url="https://admin345902.superlogica.net/publico/arquivos?accesskey=xyz",
            filename="elevador avis.pdf",
        ),
    )
    config = build_config(tmp_path)
    summary = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert summary["arquivos"] == 1  # 1 arquivo direto → 1 linha (não vira E-05)
    rows = _read_map(config.map_path)
    assert len(rows) == 1
    assert rows[0]["nome_arquivo"] == "elevador avis.pdf"
    assert "arquivos?accesskey=xyz" in rows[0]["url_download"]
    assert "E-05" not in _report_types(config)


def test_fail_soft_on_unreadable_pdf_continues(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "list_pdfs", lambda *a, **k: [DrivePdf("id1", "broken.pdf")])
    monkeypatch.setattr(pipeline, "download_pdf_bytes", lambda *a, **k: b"not a pdf")
    config = build_config(tmp_path)
    summary = pipeline.run_full(config, service=None, sleep=lambda *_: None)

    assert summary["pdfs"] == 1
    assert summary["pdfs_ok"] == 0  # ilegível não interrompe
    assert "E-02" in _report_types(config)
