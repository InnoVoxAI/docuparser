"""Leitura/validação do mapa (E-01/E-02) e reescrita de status."""

import csv

import pytest
from superlogica_file_downloader.map_io import (
    MAP_COLUMNS,
    STATUS_BAIXADO,
    MapError,
    MapRow,
    load_map,
    write_map,
)


def _write_map_csv(path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in MAP_COLUMNS})


def _sample_row(**over) -> dict:
    base = {
        "url_download": "https://x/downloadarquivo?id=1&hash=h",
        "nome_arquivo": "a.pdf",
        "fornecedor": "F",
        "categoria_bruta": "Água",
        "complemento": "junho",
        "pasta_destino": "Água",
        "hyperlink_origem": "https://x/arquivos?accesskey=k",
        "pdf_origem": "despesas.pdf",
        "status": "pendente",
    }
    base.update(over)
    return base


def test_load_map_reads_rows(tmp_path):
    path = tmp_path / "mapa_download.csv"
    _write_map_csv(path, [_sample_row()])
    rows = load_map(path)
    assert len(rows) == 1
    assert rows[0].url_download.endswith("id=1&hash=h")
    assert rows[0].pasta_destino == "Água"
    assert rows[0].status == "pendente"


def test_missing_file_is_fatal(tmp_path):
    with pytest.raises(MapError):
        load_map(tmp_path / "inexistente.csv")


def test_missing_essential_column_is_fatal(tmp_path):
    path = tmp_path / "mapa_download.csv"
    # cabeçalho sem a coluna 'status'
    cols = [c for c in MAP_COLUMNS if c != "status"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerow({c: "x" for c in cols})
    with pytest.raises(MapError):
        load_map(path)


def test_empty_url_row_loads_without_crashing(tmp_path):
    path = tmp_path / "mapa_download.csv"
    _write_map_csv(path, [_sample_row(url_download="")])
    rows = load_map(path)
    assert rows[0].url_download == ""  # E-02 tratado no download, não na carga


def test_json_map_round_trip(tmp_path):
    import json

    path = tmp_path / "mapa_download.json"
    line = json.dumps({c: _sample_row()[c] for c in MAP_COLUMNS}, ensure_ascii=False)
    path.write_text(line + "\n", encoding="utf-8")

    rows = load_map(path, "json")
    assert len(rows) == 1 and rows[0].pasta_destino == "Água"

    rows[0].status = STATUS_BAIXADO
    write_map(path, "json", rows)
    assert load_map(path, "json")[0].status == STATUS_BAIXADO


def test_json_missing_essential_column_is_fatal(tmp_path):
    import json

    path = tmp_path / "mapa_download.json"
    obj = {c: "x" for c in MAP_COLUMNS if c != "status"}
    path.write_text(json.dumps(obj) + "\n", encoding="utf-8")
    with pytest.raises(MapError):
        load_map(path, "json")


def test_write_map_preserves_columns_and_updates_status(tmp_path):
    path = tmp_path / "mapa_download.csv"
    _write_map_csv(path, [_sample_row()])
    rows = load_map(path)
    rows[0].status = STATUS_BAIXADO
    write_map(path, "csv", rows)

    reloaded = load_map(path)
    assert reloaded[0].status == STATUS_BAIXADO
    assert reloaded[0].categoria_bruta == "Água"  # conteúdo intacto (FR-004)
    assert reloaded[0].complemento == "junho"
    assert isinstance(reloaded[0], MapRow)
