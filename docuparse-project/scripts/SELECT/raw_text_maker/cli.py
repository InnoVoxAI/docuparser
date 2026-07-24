"""CLI do raw_text_maker (Typer).

Uso canônico (a partir de ``scripts/SELECT``)::

    uv run python -m raw_text_maker

Exit codes: 0 sucesso (mesmo com documentos em erro — fail-soft) · 1 falha fatal
(origem ausente, backend-ocr fora do ar) · 2 erro de uso (Typer) · 130 interrompido.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from raw_text_maker.config import OCR_RETRIES, OCR_TIMEOUT_S, build_config
from raw_text_maker.discovery import DiscoveryError
from raw_text_maker.ocr_client import ServiceUnavailable
from raw_text_maker.pipeline import run, seed_formatted_manifest
from raw_text_maker.textlayer import PyMuPDFUnavailable

app = typer.Typer(
    add_completion=False,
    help="Produz o texto bruto (.txt) de cada documento, espelhando as pastas de categoria.",
)


def _err(msg: str) -> None:
    typer.echo(msg, err=True)


@app.command()
def main(
    source_root: Path = typer.Option(
        None,
        "--source-root",
        help="Árvore com as pastas de categoria (padrão: downloads/fases/downloads).",
    ),
    output_root: Path = typer.Option(
        None,
        "--output-root",
        help="Raiz dos .txt (padrão: '<origem>/../Raw Text Docs').",
    ),
    errors: Path = typer.Option(
        None, "--errors", help="CSV de erros (padrão: <destino>/../raw_text_erros.csv)."
    ),
    ocr_url: str = typer.Option(
        None, "--ocr-url", help="URL do backend-ocr (padrão: $BACKEND_OCR_URL ou localhost:8080)."
    ),
    engine: str = typer.Option(
        None, "--engine", help="Força um engine OCR (padrão: o backend escolhe pelo tipo)."
    ),
    timeout: float = typer.Option(OCR_TIMEOUT_S, "--timeout", help="Timeout (s) por documento."),
    retries: int = typer.Option(OCR_RETRIES, "--retries", help="Tentativas em falha transitória."),
    pause: float = typer.Option(0.0, "--pause", help="Pausa (s) entre documentos."),
    formatted: bool = typer.Option(
        False,
        "--formatted",
        help="Regrava com o texto formatado (layout espacial) só os arquivos docling; "
        "scans/openrouter ficam intactos. Pula o que já consta no manifesto.",
    ),
    reformat_all: bool = typer.Option(
        False,
        "--reformat-all",
        help="Com --formatted: ignora o manifesto e reprocessa TODOS os documentos "
        "com camada de texto (comportamento anterior ao gate).",
    ),
    seed_formatted: bool = typer.Option(
        False,
        "--seed-formatted",
        help="Marca no manifesto o que já está formatado, sem chamar o backend. "
        "Migração de uma vez só para árvores anteriores ao manifesto.",
    ),
    manifest: Path = typer.Option(
        None,
        "--manifest",
        help="Manifesto de formatados (padrão: <destino>/../raw_text_formatted.csv).",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Loga cada .txt produzido."),
) -> None:
    """Varre a árvore de documentos e produz um .txt de texto bruto para cada um."""
    if retries < 1:
        _err(f"--retries inválido: {retries} (mínimo 1)")
        raise typer.Exit(2)
    if reformat_all and not formatted:
        _err("--reformat-all só faz sentido junto com --formatted.")
        raise typer.Exit(2)
    if seed_formatted and formatted:
        _err("--seed-formatted não pode ser combinado com --formatted (ele não processa nada).")
        raise typer.Exit(2)

    config = build_config(
        source_root,
        output_root=output_root,
        errors_path=errors,
        ocr_url=ocr_url,
        timeout=timeout,
        retries=retries,
        pause=pause,
        engine=engine,
        formatted=formatted,
        reformat_all=reformat_all,
        manifest_path=manifest,
    )

    try:
        if seed_formatted:
            seed_formatted_manifest(config)
        else:
            run(config, verbose=verbose)
    except (DiscoveryError, ServiceUnavailable, PyMuPDFUnavailable) as exc:
        _err(f"[FATAL] {exc}")
        raise typer.Exit(1) from exc
    except KeyboardInterrupt:
        # Interromper é esperado numa run longa; o que já virou .txt está gravado
        # e a próxima run retoma daí.
        _err("\nInterrompido. Os .txt já produzidos foram mantidos — re-rode para continuar.")
        raise typer.Exit(130) from None
    except Exception as exc:  # noqa: BLE001
        _err(f"[ERRO] Falha inesperada: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
