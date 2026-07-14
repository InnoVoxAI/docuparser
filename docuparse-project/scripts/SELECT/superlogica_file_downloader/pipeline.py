"""Orquestração da Fase B: baixa, valida, organiza e registra (fail-soft).

Itera as linhas do mapa; para cada pendente faz o Salto 3, valida, grava de
forma atômica em ``downloads/<pasta_destino>/`` e appenda no CSV final. Retoma o
que já foi baixado (status + presença em disco), registra falhas e sinaliza
provável expiração. Falhas fatais: mapa ausente (E-01) e escrita generalizada (E-08).
"""

from __future__ import annotations

import errno
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from superlogica_file_downloader.atomic import save_atomic
from superlogica_file_downloader.downloader import DownloadOutcome, download_file
from superlogica_file_downloader.map_io import (
    STATUS_BAIXADO,
    STATUS_ERRO,
    load_map,
    write_map,
)
from superlogica_file_downloader.naming import assign_final_paths
from superlogica_file_downloader.outputs import (
    ErrorRecord,
    ErrorReportWriter,
    FinalCsvWriter,
    FinalRow,
)

if TYPE_CHECKING:
    from superlogica_file_downloader.config import Config

# Erros de disco que não adianta continuar (E-08 fatal).
_FATAL_DISK_ERRNOS = {errno.ENOSPC, errno.EACCES, errno.EROFS, errno.EPERM}


class FatalError(RuntimeError):
    """Condição fatal de execução (E-08 escrita generalizada)."""


def _log(msg: str) -> None:
    print(msg)


def run(
    config: Config,
    *,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
    verbose: bool = False,
) -> dict[str, int]:
    """Executa a Fase B. Levanta ``MapError``/``FatalError`` em falhas fatais."""
    rows = load_map(config.map_path, config.map_format)  # E-01 (fatal) sobe
    final_paths = assign_final_paths(config, rows)
    summary = {"total": len(rows), "baixados": 0, "pulados": 0, "erros": 0, "expiracao": 0}

    if session is None:
        import requests

        session = requests.Session()

    with (
        FinalCsvWriter(config.final_csv_path) as final,
        ErrorReportWriter(config.errors_path) as errs,
    ):
        for row in rows:
            dest = final_paths[row.url_download]
            _process_row(config, row, dest, session, sleep, final, errs, summary, verbose)
            write_map(config.map_path, config.map_format, rows)  # progresso p/ retomada

    _print_summary(config, summary)
    return summary


def _process_row(config, row, dest, session, sleep, final, errs, summary, verbose) -> None:
    """Processa uma linha (fail-soft). Escreve status/CSV final/erro conforme o caso."""
    rel = _relpath(dest, config.work_dir)
    if row.status == STATUS_BAIXADO and dest.exists():
        summary["pulados"] += 1  # retomada: já concluído e presente (RN-4/E-12)
        if verbose:
            _log(f"  = pulado (já baixado): {rel}")
        return

    outcome = download_file(row.url_download, config, session=session, sleep=sleep)
    sleep(config.http_pause_s)  # pausa entre requisições (E-09)

    if outcome.ok:
        _save_success(config, row, dest, rel, outcome, final, summary, verbose)
    else:
        _record_error(row, outcome, errs, summary, verbose)


def _save_success(config, row, dest, rel, outcome, final, summary, verbose) -> None:
    try:
        save_atomic(dest, outcome.content or b"")
    except OSError as exc:
        if exc.errno in _FATAL_DISK_ERRNOS:
            raise FatalError(f"falha de escrita generalizada em {dest}: {exc}") from exc
        row.status = STATUS_ERRO  # falha pontual de disco (E-08) → erro e continua
        summary["erros"] += 1
        _log(f"  ! erro de escrita (pontual): {rel}: {exc}")
        return

    row.status = STATUS_BAIXADO
    final.write(
        FinalRow(
            nome_arquivo=dest.name,
            hyperlink_origem=row.hyperlink_origem,
            categoria=row.categoria_bruta,
            caminho_local=rel,
            pasta_destino=row.pasta_destino,
            fornecedor=row.fornecedor,
        )
    )
    summary["baixados"] += 1
    if verbose:
        _log(f"  + baixado: {rel}")


def _record_error(row, outcome: DownloadOutcome, errs, summary, verbose) -> None:
    row.status = STATUS_ERRO
    errs.write(
        ErrorRecord(
            url_download=row.url_download,
            motivo=outcome.motivo,
            tentativas=outcome.tentativas,
            possivel_expiracao=outcome.possivel_expiracao,
            nome_arquivo=row.nome_arquivo,
            pdf_origem=row.pdf_origem,
        )
    )
    summary["erros"] += 1
    if outcome.possivel_expiracao:
        summary["expiracao"] += 1
    if verbose:
        _log(f"  ! erro: {row.url_download} — {outcome.motivo}")


def _relpath(dest: Path, work_dir: Path) -> str:
    try:
        return os.path.relpath(dest, work_dir)
    except ValueError:  # caminhos em drives diferentes (Windows) — usa absoluto
        return str(dest)


def _print_summary(config: Config, summary: dict[str, int]) -> None:
    _log("\n[Fase B] Resumo:")
    _log(f"  Linhas no mapa:   {summary['total']}")
    _log(f"  Baixadas:         {summary['baixados']} → {config.downloads_root}")
    _log(f"  Puladas (já ok):  {summary['pulados']}")
    _log(f"  Com erro:         {summary['erros']} → {config.errors_path.name}")
    _log(f"  CSV final:        {config.final_csv_path.name}")
    if summary["expiracao"]:
        _log(
            f"\n  ⚠ {summary['expiracao']} erro(s) de POSSÍVEL EXPIRAÇÃO de accesskey/hash."
        )
        _log("    Re-rode a Fase A para renovar as URLs e depois a Fase B (retoma o que falta).")
