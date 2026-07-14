"""Salto 1 — extração do PDF: cruzar anotações de link com o texto por coordenadas.

Um PDF não tem "tabela" estrutural: tem texto posicionado e anotações de link
posicionadas, em camadas separadas (Seção 5). Aqui:

1. localiza as colunas pelos cabeçalhos conhecidos e calcula as fronteiras a
   partir das **linhas-início** (as que têm data em Vencimento). Isso é essencial
   nos PDFs "CONTAS A PAGAR", onde o nome do fornecedor quebra em várias linhas de
   endereço que invadem, à direita, a coluna da Categoria — só nas linhas-início
   fornecedor e categoria ficam bem separados;
2. usa cada hyperlink como âncora de uma linha lógica e monta a célula da
   Categoria juntando a linha-início com suas continuações **de complemento**,
   ignorando as continuações **de fornecedor** (nome/endereço longo) — assim
   células quebradas voltam a formar um único valor sem contaminar a categoria;
3. cruzamento de baixa confiança (link longe de qualquer linha, ou sem categoria)
   é sinalizado (``ambiguous`` → E-12), nunca adivinhado em silêncio.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
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


def _header_anchors(header: dict) -> dict[str, float]:
    """Posição ``x`` de cada cabeçalho de coluna (âncora de referência)."""
    starts: dict[str, float] = {}
    for x0, text in header["words"]:
        stem = _norm(text)
        for target in _HEADER_STEMS:
            if stem.startswith(target) and target not in starts:
                starts[target] = x0
    return starts


def _gap_boundary(xa: float, xb: float, spans: list[tuple], min_gap: float) -> float:
    """Fronteira entre duas colunas: meio do maior vão VAZIO entre os valores.

    ``spans`` são pares ``(x0, x1)``. Usar o fim de uma palavra e o início da
    próxima evita que uma palavra larga finja um vão. Sem um vão claro
    (≥ ``min_gap``), cai para a âncora direita ``xb`` (fronteira do cabeçalho).
    """
    inside = sorted((x0, x1) for x0, x1 in spans if xa <= x0 <= xb)
    best_gap, best_mid, prev_end = 0.0, xb, None
    for x0, x1 in inside:
        if prev_end is not None and x0 - prev_end > best_gap:
            best_gap, best_mid = x0 - prev_end, (prev_end + x0) / 2
        prev_end = x1 if prev_end is None else max(prev_end, x1)
    return best_mid if best_gap >= min_gap else xb


def _left_align_peak(spans: list[tuple], lo: float, hi: float, min_count: int) -> float | None:
    """``x`` onde muitos valores se alinham à esquerda (pico de x0) em ``(lo, hi]``.

    Colunas alinhadas à esquerda (como Categoria) têm muitas palavras começando no
    mesmo ``x``. Esse pico é robusto mesmo quando o vão some (nomes de fornecedor
    de comprimentos variados encostam na Categoria em algumas linhas).
    """
    counts = Counter(round(x0) for x0, _x1 in spans if lo < x0 <= hi)
    if not counts:
        return None
    peak, n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    return float(peak) if n >= min_count else None


def _forn_cat_boundary(
    anchors: dict[str, float], spans: list[tuple], line_h: float
) -> float:
    """Fronteira Fornecedor→Categoria: pelo alinhamento à esquerda da Categoria
    (multi-linha) ou, na falta de pico, pelo maior vão de dados."""
    forn_x, cat_x = anchors["fornecedor"], anchors["categoria"]
    peak = _left_align_peak(spans, forn_x, cat_x + 0.5 * (cat_x - forn_x), min_count=3)
    if peak is not None:
        return peak - 0.3 * line_h  # inclui os valores que começam no pico
    return _gap_boundary(forn_x, cat_x, spans, 1.5 * line_h)


def _column_ranges(
    anchors: dict[str, float], spans: list[tuple], line_h: float
) -> dict[str, tuple[float, float]]:
    """Faixas ``[lo, hi)`` de cada coluna, com fronteiras nos maiores vãos de dados."""
    ordered = sorted(anchors.items(), key=lambda kv: kv[1])
    min_gap = 1.5 * line_h
    bounds = [
        _gap_boundary(ordered[i][1], ordered[i + 1][1], spans, min_gap)
        for i in range(len(ordered) - 1)
    ]
    # Fronteira Fornecedor→Categoria: usa o alinhamento à esquerda da Categoria.
    labels = [label for label, _x in ordered]
    if "fornecedor" in labels and "categoria" in labels:
        fc_idx = labels.index("fornecedor")
        if labels[fc_idx + 1] == "categoria":
            bounds[fc_idx] = _forn_cat_boundary(anchors, spans, line_h)
    ranges: dict[str, tuple[float, float]] = {}
    for idx, (label, _x) in enumerate(ordered):
        lo = bounds[idx - 1] if idx > 0 else float("-inf")
        hi = bounds[idx] if idx < len(bounds) else float("inf")
        ranges[label] = (lo, hi)
    return ranges


def _in_column(x: float, col_range: tuple[float, float]) -> bool:
    return col_range[0] <= x < col_range[1]


def _is_row_start(line: dict, columns: dict[str, tuple[float, float]]) -> bool:
    """True se a linha inicia uma linha da tabela (tem célula curta preenchida)."""
    keys = {k for k in _ROW_START_COLUMNS if k in columns} or {"fornecedor"}
    return any(_in_column(x, columns[k]) for k in keys for x, _ in line["words"])


def _line_kind(line: dict, columns: dict[str, tuple[float, float]]) -> str:
    """``rowstart`` | ``forn`` | ``cat`` — pela coluna da palavra mais à esquerda."""
    leftmost = min(x for x, _ in line["words"])
    if "vencimento" in columns and _in_column(leftmost, columns["vencimento"]):
        return "rowstart"
    if _in_column(leftmost, columns["fornecedor"]):
        return "forn"
    return "cat"


def _row_cells(
    body: list[dict], start_idx: int, columns: dict[str, tuple[float, float]]
) -> tuple[str, str]:
    """``(fornecedor, categoria)`` da linha lógica (início + continuações).

    Continuações de **fornecedor** (nome/endereço longo que invade a coluna da
    Categoria) não entram na categoria; continuações de **complemento** entram.
    """
    forn_range, cat_range = columns["fornecedor"], columns["categoria"]
    forn: list[tuple] = []
    cat: list[tuple] = []
    for j in range(start_idx, len(body)):
        line = body[j]
        if j > start_idx and _is_row_start(line, columns):
            break
        kind = _line_kind(line, columns)
        for x, t in line["words"]:
            if _in_column(x, forn_range):
                forn.append((line["cy"], x, t))
            elif kind != "forn" and _in_column(x, cat_range):
                cat.append((line["cy"], x, t))
    forn_text = " ".join(t for _, _, t in sorted(forn)).strip()
    cat_text = " ".join(t for _, _, t in sorted(cat)).strip()
    return forn_text, cat_text


def _anchor(body: list[dict], cy: float, columns: dict, max_gap: float):
    """Índice da linha-início associada ao link e se o casamento é incerto."""
    if not body:
        return None, True
    idx = min(range(len(body)), key=lambda i: abs(body[i]["cy"] - cy))
    ambiguous = abs(body[idx]["cy"] - cy) > max_gap
    while idx > 0 and not _is_row_start(body[idx], columns):
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


def _row_start_spans(body: list[dict], words: list[tuple], anchors: dict, tol: float):
    """Spans ``(x0, x1)`` apenas das linhas-início (têm data à esquerda do Fornecedor).

    É nelas que Fornecedor e Categoria ficam separados por um vão limpo — as
    continuações de endereço do fornecedor sobrepõem as colunas e são excluídas.
    """
    threshold = (anchors.get("vencimento", anchors["fornecedor"]) + anchors["fornecedor"]) / 2
    rs_cys = [ln["cy"] for ln in body if min(x for x, _ in ln["words"]) < threshold]
    spans = [
        (w[0], w[2])
        for w in words
        if any(abs((w[1] + w[3]) / 2 - rc) <= tol for rc in rs_cys)
    ]
    return spans or [(w[0], w[2]) for w in words]


def _extract_page(page, pdf_name: str, y_tolerance_ratio: float) -> list[ExtractedLink]:
    words = page.get_text("words")
    links = [ln for ln in page.get_links() if ln.get("uri")]
    if not words or not links:
        return []
    heights = [w[3] - w[1] for w in words if w[3] > w[1]]
    line_h = statistics.median(heights) if heights else 10.0
    lines = _cluster_lines(words, tol=0.6 * line_h)
    header = _header_line(lines)
    if header is None:
        return []  # sem cabeçalho reconhecível → caller registra E-02
    anchors = _header_anchors(header)
    if "fornecedor" not in anchors or "categoria" not in anchors:
        return []

    floor = header["cy"] + 0.5 * line_h
    body = sorted((ln for ln in lines if ln["cy"] > floor), key=lambda ln: ln["cy"])
    spans = _row_start_spans(body, words, anchors, tol=0.6 * line_h)
    columns = _column_ranges(anchors, spans, line_h)
    max_gap = max(2.5, 1.0 + 3.0 * y_tolerance_ratio) * line_h

    out: list[ExtractedLink] = []
    link_anchors = sorted(((lk["from"].y0 + lk["from"].y1) / 2, lk["uri"]) for lk in links)
    for cy, uri in link_anchors:
        idx, ambiguous = _anchor(body, cy, columns, max_gap)
        if idx is None:
            out.append(ExtractedLink(pdf_name, uri, "", "", ambiguous=True))
            continue
        fornecedor, categoria = _row_cells(body, idx, columns)
        out.append(
            ExtractedLink(
                pdf_name, uri, fornecedor, categoria, ambiguous=ambiguous or not categoria
            )
        )
    return out
