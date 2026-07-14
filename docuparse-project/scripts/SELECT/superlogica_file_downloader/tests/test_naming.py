"""Nomeação: fallback, extensão e anti-colisão determinística (E-06/E-07)."""

from superlogica_file_downloader.config import build_config
from superlogica_file_downloader.map_io import MapRow
from superlogica_file_downloader.naming import assign_final_paths, base_name


def _row(url_id: str, nome: str, pasta: str = "P", fornecedor: str = "F") -> MapRow:
    return MapRow(
        url_download=f"https://x/downloadarquivo?id={url_id}&hash=h",
        nome_arquivo=nome,
        fornecedor=fornecedor,
        pasta_destino=pasta,
    )


def test_base_name_keeps_pdf_extension():
    assert base_name(_row("1", "img20260602.pdf")) == "img20260602.pdf"


def test_base_name_adds_pdf_extension_when_missing():
    assert base_name(_row("1", "recibo")) == "recibo.pdf"


def test_base_name_fallback_when_empty():
    name = base_name(_row("112235", "", fornecedor="Bombas Ltda"))
    assert name == "Bombas_Ltda_112235.pdf"


def test_collision_gets_deterministic_id_prefix(tmp_path):
    config = build_config(tmp_path)
    rows = [_row("111", "img.pdf"), _row("222", "img.pdf"), _row("333", "solo.pdf")]
    paths = assign_final_paths(config, rows)

    # As duas linhas que colidiriam recebem o prefixo {id}_ (determinístico).
    assert paths[rows[0].url_download].name == "111_img.pdf"
    assert paths[rows[1].url_download].name == "222_img.pdf"
    # A linha sem colisão mantém o nome simples.
    assert paths[rows[2].url_download].name == "solo.pdf"


def test_assignment_is_stable_across_calls(tmp_path):
    config = build_config(tmp_path)
    rows = [_row("111", "img.pdf"), _row("222", "img.pdf")]
    first = assign_final_paths(config, rows)
    second = assign_final_paths(config, rows)
    assert first == second  # mesma entrada → mesmos caminhos (idempotência)


def test_pasta_destino_routes_under_downloads_root(tmp_path):
    config = build_config(tmp_path)
    paths = assign_final_paths(config, [_row("1", "a.pdf", pasta="Construção-Reformas")])
    dest = next(iter(paths.values()))
    assert dest.parent == config.downloads_root / "Construção-Reformas"
