"""CLI da Fase B (Typer).

Uso canônico (a partir de ``scripts/SELECT``)::

    uv run python -m superlogica_file_downloader --work-dir downloads/fases

Exit codes: 0 sucesso (mesmo com linhas em erro — fail-soft) · 1 falha fatal
(mapa ausente/ilegível E-01, escrita generalizada E-08) · 2 erro de uso (Typer).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from superlogica_file_downloader.config import MAP_FORMAT_DEFAULT, build_config
from superlogica_file_downloader.map_io import MapError
from superlogica_file_downloader.pipeline import FatalError, run

app = typer.Typer(add_completion=False, help="Fase B — baixa e organiza os arquivos do mapa.")


def _err(msg: str) -> None:
    typer.echo(msg, err=True)


@app.command()
def main(
    work_dir: Path = typer.Option(
        Path("."), "--work-dir", help="Raiz do mapa e das saídas (padrão: diretório atual)."
    ),
    map_path: Path | None = typer.Option(
        None, "--map", help="Caminho do mapa de entrada (padrão: <work-dir>/mapa_download.csv)."
    ),
    map_format: str = typer.Option(
        MAP_FORMAT_DEFAULT, "--map-format", help="Formato do mapa: csv ou json."
    ),
    downloads_root: Path | None = typer.Option(
        None, "--downloads-root", help="Raiz das pastas de destino (padrão: <work-dir>/downloads)."
    ),
    final_csv: Path | None = typer.Option(
        None, "--final-csv", help="Caminho do CSV final (padrão: <work-dir>/relatorio_final.csv)."
    ),
    errors: Path | None = typer.Option(
        None, "--errors", help="Relatório de erros (padrão: <work-dir>/fase_b_erros.csv)."
    ),
    pause: float = typer.Option(1.0, "--pause", help="Pausa (s) entre requisições."),
    timeout: float = typer.Option(30.0, "--timeout", help="Timeout (s) por requisição."),
    retries: int = typer.Option(3, "--retries", help="Tentativas antes de marcar erro."),
    pdf_only: bool = typer.Option(
        False,
        "--pdf-only",
        help="Aceitar só PDF (rejeita comprovantes em imagem). Padrão: aceita PDF e imagens.",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Log linha a linha do progresso."),
) -> None:
    """Baixa cada arquivo pendente do mapa e organiza em downloads/<pasta_destino>/."""
    if map_format not in ("csv", "json"):
        _err(f"--map-format inválido: {map_format!r} (use csv ou json)")
        raise typer.Exit(2)

    config = build_config(
        work_dir,
        map_format=map_format,
        map_path=map_path,
        downloads_root=downloads_root,
        final_csv_path=final_csv,
        errors_path=errors,
        pause=pause,
        timeout=timeout,
        retries=retries,
        accept_images=not pdf_only,
    )
    typer.echo(f"[Fase B] work-dir: {config.work_dir}")

    try:
        run(config, verbose=verbose)
    except (MapError, FatalError) as exc:
        _err(f"[FATAL] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        _err(f"[ERRO] Falha inesperada: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
