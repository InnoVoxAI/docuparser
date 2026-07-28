"""Entrypoint: ``python -m superlogica_file_downloader``.

Execução canônica (a partir do diretório ``scripts/SELECT``, que contém o pacote)::

    uv run python -m superlogica_file_downloader --work-dir downloads/fases

O ``--work-dir`` aponta para onde está o ``mapa_download.csv`` (produzido pela
Fase A) e onde as saídas (``relatorio_final.csv`` etc.) serão gravadas.
"""

from superlogica_file_downloader.cli import app

if __name__ == "__main__":
    app()
