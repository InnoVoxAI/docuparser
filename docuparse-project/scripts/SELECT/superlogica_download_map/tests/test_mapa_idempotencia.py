"""Testes do writer do mapa: idempotência + escrita incremental (T028).

Tocam disco via ``tmp_path`` → são testes de integração do writer (não marcados
``unit``, conforme a regra da constituição de que unit tests não tocam disco).
"""

import csv
import json

import pytest

from superlogica_download_map.mapa import (
    STATUS_PENDENTE,
    MapEntry,
    MapWriter,
    ProvenanceError,
)


def _entry(url: str, name: str = "a.pdf", pasta: str = "Água") -> MapEntry:
    return MapEntry(
        url_download=url,
        nome_arquivo=name,
        fornecedor="Fornecedor X",
        categoria_bruta="Água",
        complemento="",
        pasta_destino=pasta,
        hyperlink_origem="https://exemplo/arquivos?accesskey=abc",
        pdf_origem="despesas.pdf",
    )


def _rows(path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_writes_header_and_rows(tmp_path):
    p = tmp_path / "mapa.csv"
    with MapWriter(p) as w:
        assert w.write(_entry("u1")) is True
        assert w.write(_entry("u2", "b.pdf")) is True
    rows = _rows(p)
    assert [r["url_download"] for r in rows] == ["u1", "u2"]
    assert rows[0]["status"] == STATUS_PENDENTE


def test_dedup_within_run(tmp_path):
    p = tmp_path / "mapa.csv"
    with MapWriter(p) as w:
        assert w.write(_entry("u1")) is True
        assert w.write(_entry("u1")) is False
    assert len(_rows(p)) == 1


def test_idempotent_across_runs(tmp_path):
    p = tmp_path / "mapa.csv"
    with MapWriter(p) as w:
        w.write(_entry("u1"))
    with MapWriter(p) as w:  # nova execução: carrega url existentes
        assert w.already_mapped("u1") is True
        assert w.write(_entry("u1")) is False
        assert w.write(_entry("u2")) is True
    assert p.read_text(encoding="utf-8").count("url_download") == 1  # header uma vez
    assert [r["url_download"] for r in _rows(p)] == ["u1", "u2"]


def test_incremental_flush_survives_interruption(tmp_path):
    p = tmp_path / "mapa.csv"
    with MapWriter(p) as w:
        w.write(_entry("u1"))
        # lê do disco com o writer ainda aberto (simula interrupção no meio)
        assert [r["url_download"] for r in _rows(p)] == ["u1"]


def test_provenance_error_on_missing_field(tmp_path):
    p = tmp_path / "mapa.csv"
    bad = _entry("u1")
    bad.pdf_origem = ""
    with MapWriter(p) as w, pytest.raises(ProvenanceError):
        w.write(bad)


def test_json_lines_format(tmp_path):
    p = tmp_path / "mapa.json"
    with MapWriter(p, fmt="json") as w:
        w.write(_entry("u1"))
        w.write(_entry("u2"))
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["url_download"] == "u1"
