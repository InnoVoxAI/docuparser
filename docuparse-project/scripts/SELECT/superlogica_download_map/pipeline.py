"""Orquestração da Fase A: navega os saltos e grava o mapa (fail-soft).

- :func:`run_full` — execução completa (US1–US4).
- :func:`run_recon` — passada de reconhecimento de categorias (US5).

Exceções não-fatais são registradas no relatório e a execução continua; apenas
falhas de autenticação são fatais (tratadas na CLI).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from superlogica_download_map.categorizer import (
    aggregate_categories,
    categorize,
    split_categoria_complemento,
)
from superlogica_download_map.config import FALLBACK_FOLDER
from superlogica_download_map.drive_reader import download_pdf_bytes, list_pdfs
from superlogica_download_map.mapa import MapEntry, MapWriter, ProvenanceError
from superlogica_download_map.pdf_extractor import ExtractedLink, extract_links_from_pdf
from superlogica_download_map.reports import ExceptionReport, write_categories
from superlogica_download_map.sanitize import sanitize
from superlogica_download_map.superlogica import (
    SuperlogicaError,
    fallback_filename,
    fetch_page,
    parse_download_anchors,
)

if TYPE_CHECKING:
    from superlogica_download_map.config import Config


def _log(msg: str) -> None:
    print(msg)


def _read_links(service, pdf, config, report: ExceptionReport) -> list[ExtractedLink] | None:
    """Baixa e extrai um PDF; None sinaliza E-02 (ilegível), já registrado."""
    try:
        data = download_pdf_bytes(service, pdf.id)
        return extract_links_from_pdf(data, pdf.name, y_tolerance_ratio=config.y_tolerance_ratio)
    except Exception as exc:  # noqa: BLE001 — PDF ilegível/corrompido
        report.add("E-02", pdf.name, f"PDF ilegível/sem tabela: {exc}", "pulado")
        return None


def run_full(
    config: Config,
    service,
    *,
    verbose: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, int]:
    """Descobre e cataloga todos os arquivos a baixar (não baixa nada)."""
    import requests

    report = ExceptionReport()
    summary = {"pdfs": 0, "pdfs_ok": 0, "hyperlinks": 0, "arquivos": 0}

    pdfs = list_pdfs(service, config.drive_folder_ids, recursive=config.recursive)
    _log(f"[Fase A] {len(pdfs)} PDF(s) encontrados:")
    for pdf in pdfs:
        _log(f"  - {pdf.name}")

    session = requests.Session()
    with MapWriter(config.map_path, fmt=config.map_format) as writer:
        for pdf in pdfs:
            summary["pdfs"] += 1
            links = _read_links(service, pdf, config, report)
            if links is None:
                continue
            summary["pdfs_ok"] += 1
            for link in links:
                summary["hyperlinks"] += 1
                _process_link(link, config, session, writer, report, summary, verbose)
                sleep(config.http_pause_s)  # pausa entre requisições (E-10)

    report.write_csv(config.report_path)
    _print_summary(config, summary, report)
    return summary


def _process_link(link, config, session, writer, report, summary, verbose) -> None:
    """Resolve um hyperlink no Superlógica e grava uma linha por âncora."""
    categoria, complemento = split_categoria_complemento(link.categoria_complemento_raw)
    pasta = categorize(categoria, family_rules=config.family_rules)
    origem = f"{link.pdf_origem} | {link.fornecedor}"
    if pasta == FALLBACK_FOLDER:
        report.add("E-07", origem, "categoria indeterminada", "→ _A_Revisar")
    if link.ambiguous:
        report.add("E-12", origem, "cruzamento de baixa confiança", "revisar cruzamento")

    try:
        html = fetch_page(link.hyperlink_origem, config, session=session)
    except SuperlogicaError as exc:
        report.add("E-04", f"{origem} | {link.hyperlink_origem}", str(exc), "pulado")
        return

    anchors = parse_download_anchors(html)
    if not anchors:
        report.add("E-05", f"{origem} | {link.hyperlink_origem}", "página sem âncoras", "pulado")
        return

    _ensure_folder(config, pasta)
    for url_download, nome in anchors:
        entry = _build_entry(link, categoria, complemento, pasta, url_download, nome, report)
        try:
            if writer.write(entry):
                summary["arquivos"] += 1
        except ProvenanceError as exc:
            report.add("E-12", url_download, f"proveniência incompleta: {exc}", "descartada")


def _build_entry(link, categoria, complemento, pasta, url_download, nome, report) -> MapEntry:
    fallback = fallback_filename(link.fornecedor, url_download)
    if not nome:
        report.add("E-06", url_download, "nome real ausente no title", "fallback de nome")
        nome = fallback
    return MapEntry(
        url_download=url_download,
        nome_arquivo=sanitize(nome, fallback=fallback),
        fornecedor=link.fornecedor,
        categoria_bruta=categoria,
        complemento=complemento,
        pasta_destino=pasta,
        hyperlink_origem=link.hyperlink_origem,
        pdf_origem=link.pdf_origem,
    )


def _ensure_folder(config: Config, pasta: str) -> None:
    (config.downloads_root / pasta).mkdir(parents=True, exist_ok=True)


def run_recon(config: Config, service, *, verbose: bool = False) -> dict[str, int]:
    """Passada de reconhecimento: inventário de categorias distintas (US5)."""
    report = ExceptionReport()
    pdfs = list_pdfs(service, config.drive_folder_ids, recursive=config.recursive)
    _log(f"[Fase A · recon] {len(pdfs)} PDF(s) encontrados.")

    cells: list[str] = []
    for pdf in pdfs:
        links = _read_links(service, pdf, config, report)
        if links is None:
            continue
        cells.extend(link.categoria_complemento_raw for link in links)

    rows = aggregate_categories(cells, family_rules=config.family_rules)
    write_categories(config.categories_path, rows)
    if len(report):
        report.write_csv(config.report_path)
    _log(f"[Fase A · recon] {len(rows)} categoria(s) distinta(s) → {config.categories_path.name}")
    _log("Revise as pasta_destino_propostas e ajuste FAMILY_RULES antes de gerar o mapa.")
    return {"pdfs": len(pdfs), "categorias": len(rows)}


def _print_summary(config: Config, summary: dict[str, int], report: ExceptionReport) -> None:
    _log("\n[Fase A] Resumo:")
    _log(f"  PDFs lidos:            {summary['pdfs']} (legíveis: {summary['pdfs_ok']})")
    _log(f"  Hyperlinks resolvidos: {summary['hyperlinks']}")
    _log(f"  Arquivos mapeados:     {summary['arquivos']} → {config.map_path.name}")
    counts = report.counts_by_type()
    if counts:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        _log(f"  Exceções ({len(report)}): {detail} → {config.report_path.name}")
    else:
        _log("  Exceções: 0")
    _log("  (Nenhum arquivo-alvo baixado — isso é a Fase B.)")
