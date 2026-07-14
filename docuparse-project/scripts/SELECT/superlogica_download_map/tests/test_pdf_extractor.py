"""Test do cruzamento link↔categoria em PDF sintético (T012).

Gera um PDF com cabeçalho + uma linha de dados e uma anotação de link sobre a
coluna Fornecedor, e verifica que a extração casa o fornecedor e a célula
"Categoria - Complemento" da mesma linha.
"""

import pymupdf
import pytest

from superlogica_download_map.categorizer import categorize, split_categoria_complemento
from superlogica_download_map.pdf_extractor import extract_links_from_pdf

_URI = "https://admin345902.superlogica.net/clients/areadocondomino/publico/arquivos?accesskey=xyz"


def _build_pdf(*, link_y: float = 122.0) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    header = [
        (50, "Vencimento"),
        (150, "Fornecedor"),
        (300, "Categoria - Complemento"),
        (500, "Compet."),
        (560, "Valor"),
    ]
    row = [
        (50, "22/06/2026"),
        (150, "SINGULAR ENGENHARIA"),
        (300, "Construção-Reformas - IMPERMEABILIZACAO"),
        (500, "06/2026"),
        (560, "2.500,00"),
    ]
    for x, text in header:
        page.insert_text((x, 100), text, fontsize=10)
    for x, text in row:
        page.insert_text((x, 130), text, fontsize=10)
    page.insert_link(
        {"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(150, link_y, 290, link_y + 13), "uri": _URI}
    )
    return doc.tobytes()


def test_crosses_link_to_supplier_and_category():
    links = extract_links_from_pdf(_build_pdf(), "despesas.pdf")
    assert len(links) == 1
    link = links[0]
    assert link.hyperlink_origem == _URI
    assert "SINGULAR" in link.fornecedor
    assert link.categoria_complemento_raw.startswith("Construção-Reformas")
    assert link.ambiguous is False
    assert link.pdf_origem == "despesas.pdf"


def test_extracted_cell_splits_and_categorizes():
    link = extract_links_from_pdf(_build_pdf(), "despesas.pdf")[0]
    categoria, _complemento = split_categoria_complemento(link.categoria_complemento_raw)
    assert categoria == "Construção-Reformas"
    assert categorize(categoria) == "Construção-Reformas"


def test_link_far_from_any_row_is_flagged_ambiguous():
    # link em y=400, longe das linhas de texto (100/130) → baixa confiança (E-12)
    links = extract_links_from_pdf(_build_pdf(link_y=400.0), "despesas.pdf")
    assert len(links) == 1
    assert links[0].ambiguous is True


def _build_wrapped_pdf() -> bytes:
    """PDF onde a célula Categoria - Complemento quebra em DUAS linhas."""
    doc = pymupdf.open()
    page = doc.new_page()
    for x, text in [(50, "Vencimento"), (150, "Fornecedor"), (300, "Categoria - Complemento"),
                    (500, "Compet."), (560, "Valor")]:
        page.insert_text((x, 100), text, fontsize=10)
    # linha principal (com o link) — categoria + início do complemento
    page.insert_text((50, 130), "22/06/2026", fontsize=10)
    page.insert_text((150, 130), "BOMBAS LTDA", fontsize=10)
    page.insert_text((300, 130), "Manut. de Bombas - SUBSTITUIÇAO DE", fontsize=10)
    page.insert_text((500, 130), "06/2026", fontsize=10)
    # linha de CONTINUAÇÃO (só a coluna de categoria) — resto do complemento
    page.insert_text((300, 144), "ROLAMENTOS PARC 2/3", fontsize=10)
    page.insert_link(
        {"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(150, 122, 290, 135), "uri": _URI}
    )
    return doc.tobytes()


def test_wrapped_cell_is_merged_into_single_category():
    links = extract_links_from_pdf(_build_wrapped_pdf(), "despesas.pdf")
    assert len(links) == 1  # uma linha lógica, não duas
    raw = links[0].categoria_complemento_raw
    categoria, complemento = split_categoria_complemento(raw)
    assert categoria == "Manut. de Bombas"          # não vira fragmento "de Bombas"
    assert "ROLAMENTOS" in complemento              # a continuação foi mesclada
    assert categorize(categoria) == "Manutenções"


def _build_pdf_with_linkless_neighbor() -> bytes:
    """Duas linhas de tabela; só a primeira tem link. A segunda (sem link) NÃO
    pode contaminar a categoria da primeira (E-03)."""
    doc = pymupdf.open()
    page = doc.new_page()
    for x, text in [(50, "Vencimento"), (150, "Fornecedor"), (300, "Categoria - Complemento"),
                    (500, "Compet."), (560, "Valor")]:
        page.insert_text((x, 100), text, fontsize=10)
    # linha 1 (com link)
    page.insert_text((50, 130), "01/06/2026", fontsize=10)
    page.insert_text((150, 130), "AGUA LTDA", fontsize=10)
    page.insert_text((300, 130), "Água e Esgoto - Junho", fontsize=10)
    page.insert_text((500, 130), "06/2026", fontsize=10)
    # linha 2 (SEM link) — categoria totalmente diferente
    page.insert_text((50, 160), "02/06/2026", fontsize=10)
    page.insert_text((150, 160), "OBRAS SA", fontsize=10)
    page.insert_text((300, 160), "Construção-Reformas - OBRA", fontsize=10)
    page.insert_text((500, 160), "06/2026", fontsize=10)
    page.insert_link(
        {"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(150, 122, 290, 135), "uri": _URI}
    )
    return doc.tobytes()


def test_linkless_neighbor_row_does_not_contaminate():
    links = extract_links_from_pdf(_build_pdf_with_linkless_neighbor(), "despesas.pdf")
    assert len(links) == 1  # só a linha com link vira registro
    raw = links[0].categoria_complemento_raw
    assert "Água e Esgoto" in raw
    assert "Construção" not in raw and "OBRA" not in raw  # sem vazamento da linha vizinha


def test_corrupt_pdf_raises():
    with pytest.raises(pymupdf.FileDataError):
        extract_links_from_pdf(b"not a pdf", "broken.pdf")
