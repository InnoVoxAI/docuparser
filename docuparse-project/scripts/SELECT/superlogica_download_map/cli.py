"""CLI da Fase A (Typer).

Uso canônico (a partir de ``scripts/SELECT``)::

    uv run python -m superlogica_download_map --work-dir downloads/fases

Exit codes: 0 sucesso · 2 falha fatal de autenticação (E-01) · 1 erro inesperado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from superlogica_download_map.config import (
    MAP_FORMAT_DEFAULT,
    RECURSIVE_DEFAULT,
    build_config,
)
from superlogica_download_map.drive_auth import AuthError

app = typer.Typer(add_completion=False, help="Fase A — gera o mapa de download.")


def _echo(msg: str) -> None:
    typer.echo(msg)


def _err(msg: str) -> None:
    typer.echo(msg, err=True)


@app.command()
def main(
    work_dir: Path = typer.Option(
        Path("."), "--work-dir", help="Raiz de credenciais e saídas (padrão: diretório atual)."
    ),
    recon: bool = typer.Option(
        False, "--recon", help="Executa só a passada de reconhecimento de categorias e para."
    ),
    recursive: bool = typer.Option(
        RECURSIVE_DEFAULT, "--recursive/--no-recursive", help="Varrer subpastas do Drive."
    ),
    map_format: str = typer.Option(
        MAP_FORMAT_DEFAULT, "--map-format", help="Formato do mapa: csv ou json."
    ),
    credentials: Path | None = typer.Option(
        None, "--credentials", help="Caminho do credentials.json (padrão: no --work-dir)."
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Log em nível debug."),
) -> None:
    """Descobre e cataloga os arquivos a baixar na Fase B (não baixa nada aqui)."""
    if map_format not in ("csv", "json"):
        _err(f"--map-format inválido: {map_format!r} (use csv ou json)")
        raise typer.Exit(1)

    config = build_config(
        work_dir, map_format=map_format, recursive=recursive, credentials=credentials
    )
    _echo(f"[Fase A] work-dir: {config.work_dir}")

    # Autenticação (marco: falha aqui é fatal — E-01).
    try:
        from superlogica_download_map.drive_auth import build_drive_service, get_credentials

        creds = get_credentials(config)
        service = build_drive_service(creds)
    except AuthError as exc:
        _err(f"[FATAL] {exc}")
        raise typer.Exit(2) from exc

    try:
        if recon:
            from superlogica_download_map.pipeline import run_recon

            run_recon(config, service, verbose=verbose)
        else:
            from superlogica_download_map.pipeline import run_full

            run_full(config, service, verbose=verbose)
    except AuthError as exc:  # token revogado no meio da execução
        _err(f"[FATAL] {exc}")
        raise typer.Exit(2) from exc
    except Exception as exc:  # noqa: BLE001
        _err(f"[ERRO] Falha inesperada: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
