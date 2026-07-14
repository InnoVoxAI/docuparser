"""Salto 1 — extração do PDF: cruzar anotações de link com o texto por coordenadas.

Um PDF não tem "tabela" estrutural: tem texto posicionado e anotações de link
posicionadas, em camadas separadas (Seção 5). Aqui:

1. localiza as colunas pelo cabeçalho conhecido (Fornecedor, Categoria - Complemento…);
2. agrupa o texto em linhas físicas e distingue **início de linha da tabela**
   (tem data em Vencimento / valor em Valor) de **linha de continuação** (só a
   célula que quebrou, tipicamente o complemento longo);
3. usa cada hyperlink como âncora de uma linha lógica e **mescla a linha-início
   com suas continuações** — assim células quebradas voltam a formar um único
   valor (corrige fragmentos como "de Bombas", "- MAIO"), sem absorver linhas de
   despesas vizinhas que não têm link (E-03).

Cruzamento de baixa confiança (link longe de qualquer linha, ou sem categoria) é
sinalizado (``ambiguous`` → E-12), nunca adivinhado em silêncio.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

# Stems normalizados dos cabeçalhos de coluna, na ordem esperada.
_HEADER_STEMS = ("vencimento", "fornecedor", "categoria", "compet", "valor")
# Colunas curtas que só aparecem no início de uma linha da tabela (não em wraps).
_ROW_START_COLUMNS = ("vencimento", "valor", "compet")


@dataclass
class ExtractedLink:
    pdf_origem: str
    hyperlink_origem: str
    fornecedor: str
    categoria_complemento_raw: str
    ambiguous: bool = False


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _cluster_lines(words: list[tuple], tol: float) -> list[dict]:
    """Agrupa palavras em linhas físicas por proximidade do centro vertical."""
    enriched = sorted(((w[1] + w[3]) / 2, w[0], w[4]) for w in words)
    lines: list[dict] = []
    for cy, x0, text in enriched:
        if lines and abs(cy - lines[-1]["cy"]) <= tol:
            line = lines[-1]
            line["words"].append((x0, text))
            line["cy"] = (line["cy"] * line["n"] + cy) / (line["n"] + 1)
            line["n"] += 1
        else:
            lines.append({"cy": cy, "n": 1, "words": [(x0, text)]})
    for line in lines:
        line["words"].sort()
    return lines


def _header_line(lines: list[dict]) -> dict | None:
    for line in lines:
        joined = "".join(_norm(t) for _, t in line["words"])
        if "fornecedor" in joined and "categoria" in joined:
            return line
    return None


def _find_columns(lines: list[dict]) -> dict[str, tuple[float, float]]:
    """Mapeia cada coluna para sua faixa horizontal ``[x_start, x_end)``."""
    header = _header_line(lines)
    if header is None:
        return {}
    starts: dict[str, float] = {}
    for x0, text in header["words"]:
        stem = _norm(text)
        for target in _HEADER_STEMS:
            if stem.startswith(target) and target not in starts:
                starts[target] = x0
    if "fornecedor" not in starts or "categoria" not in starts:
        return {}
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    ranges: dict[str, tuple[float, float]] = {}
    for idx, (label, x_start) in enumerate(ordered):
        x_end = ordered[idx + 1][1] if idx + 1 < len(ordered) else float("inf")
        ranges[label] = (x_start, x_end)
    return ranges


def _in_column(x: float, col_range: tuple[float, float], pad: float) -> bool:
    return col_range[0] - pad <= x < col_range[1] - pad


def _is_row_start(line: dict, columns: dict, pad: float) -> bool:
    """True se a linha inicia uma linha da tabela (tem célula curta preenchida)."""
    keys = [k for k in _ROW_START_COLUMNS if k in columns] or ["fornecedor"]
    return any(
        _in_column(x, columns[key], pad) for key in keys for x, _ in line["words"]
    )


def _merge_row(body: list[dict], start_idx: int, columns: dict, pad: float) -> list[tuple]:
    """Junta a linha-início com suas continuações (até a próxima linha-início)."""
    words: list[tuple] = []
    for j in range(start_idx, len(body)):
        if j > start_idx and _is_row_start(body[j], columns, pad):
            break
        cy = body[j]["cy"]
        words.extend((cy, x, t) for x, t in body[j]["words"])
    return words


def _cell_words(words: list[tuple], col_range: tuple[float, float], pad: float) -> str:
    """Texto da coluna em ordem de leitura (y, depois x)."""
    cell = sorted((y, x, t) for y, x, t in words if _in_column(x, col_range, pad))
    return " ".join(t for _, _, t in cell).strip()


def _anchor(body: list[dict], cy: float, columns: dict, pad: float, max_gap: float):
    """Índice da linha-início associada ao link e se o casamento é incerto."""
    if not body:
        return None, True
    idx = min(range(len(body)), key=lambda i: abs(body[i]["cy"] - cy))
    ambiguous = abs(body[idx]["cy"] - cy) > max_gap
    while idx > 0 and not _is_row_start(body[idx], columns, pad):
        idx -= 1
    return idx, ambiguous


def extract_links_from_pdf(
    pdf_bytes: bytes, pdf_name: str, *, y_tolerance_ratio: float = 0.5
) -> list[ExtractedLink]:
    """Extrai (hyperlink, fornecedor, célula categoria) de um PDF-lista.

    Levanta exceção se o PDF não puder ser aberto (caller trata como E-02).
    """
    import pymupdf

    results: list[ExtractedLink] = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            results.extend(_extract_page(page, pdf_name, y_tolerance_ratio))
    return results


def _extract_page(page, pdf_name: str, y_tolerance_ratio: float) -> list[ExtractedLink]:
    words = page.get_text("words")
    links = [ln for ln in page.get_links() if ln.get("uri")]
    if not words or not links:
        return []
    heights = [w[3] - w[1] for w in words if w[3] > w[1]]
    line_h = statistics.median(heights) if heights else 10.0
    lines = _cluster_lines(words, tol=0.6 * line_h)
    columns = _find_columns(lines)
    if not columns:
        return []  # sem cabeçalho reconhecível → caller registra E-02

    header = _header_line(lines)
    hdr_cy = header["cy"] if header else float("-inf")
    body = sorted(
        (ln for ln in lines if ln["cy"] > hdr_cy + 0.5 * line_h), key=lambda ln: ln["cy"]
    )
    pad = 0.4 * line_h
    max_gap = max(2.5, 1.0 + 3.0 * y_tolerance_ratio) * line_h

    out: list[ExtractedLink] = []
    anchors = sorted(((lk["from"].y0 + lk["from"].y1) / 2, lk["uri"]) for lk in links)
    for cy, uri in anchors:
        idx, ambiguous = _anchor(body, cy, columns, pad, max_gap)
        if idx is None:
            out.append(ExtractedLink(pdf_name, uri, "", "", ambiguous=True))
            continue
        row = _merge_row(body, idx, columns, pad)
        fornecedor = _cell_words(row, columns["fornecedor"], pad)
        categoria = _cell_words(row, columns["categoria"], pad)
        out.append(
            ExtractedLink(
                pdf_name, uri, fornecedor, categoria, ambiguous=ambiguous or not categoria
            )
        )
    return out
