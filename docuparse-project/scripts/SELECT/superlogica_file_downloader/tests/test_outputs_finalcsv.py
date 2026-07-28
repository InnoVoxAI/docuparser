"""CSV final: append incremental + dedup por caminho_local (RN-5/RN-6)."""

import csv

from superlogica_file_downloader.config import FINAL_COLUMNS
from superlogica_file_downloader.outputs import FinalCsvWriter, FinalRow


def _row(caminho: str) -> FinalRow:
    return FinalRow(
        nome_arquivo=caminho.split("/")[-1],
        hyperlink_origem="https://x/arquivos?accesskey=k",
        categoria="Água",
        caminho_local=caminho,
        pasta_destino="Água",
        fornecedor="F",
    )


def _read(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_writes_header_and_rows_incrementally(tmp_path):
    path = tmp_path / "relatorio_final.csv"
    with FinalCsvWriter(path) as writer:
        assert writer.write(_row("downloads/Água/a.pdf")) is True
        assert writer.write(_row("downloads/Água/b.pdf")) is True
    rows = _read(path)
    assert [r["caminho_local"] for r in rows] == ["downloads/Água/a.pdf", "downloads/Água/b.pdf"]
    assert list(rows[0].keys()) == list(FINAL_COLUMNS)


def test_dedup_within_same_writer(tmp_path):
    path = tmp_path / "relatorio_final.csv"
    with FinalCsvWriter(path) as writer:
        assert writer.write(_row("downloads/Água/a.pdf")) is True
        assert writer.write(_row("downloads/Água/a.pdf")) is False  # duplicata
    assert len(_read(path)) == 1


def test_dedup_across_reopen_preserves_existing(tmp_path):
    path = tmp_path / "relatorio_final.csv"
    with FinalCsvWriter(path) as writer:
        writer.write(_row("downloads/Água/a.pdf"))
    # reabre (reexecução): a linha já existente não é regravada
    with FinalCsvWriter(path) as writer:
        assert writer.already_written("downloads/Água/a.pdf") is True
        assert writer.write(_row("downloads/Água/a.pdf")) is False
        assert writer.write(_row("downloads/Água/c.pdf")) is True
    rows = _read(path)
    assert [r["caminho_local"] for r in rows] == ["downloads/Água/a.pdf", "downloads/Água/c.pdf"]
