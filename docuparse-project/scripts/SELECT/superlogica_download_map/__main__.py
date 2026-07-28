"""Entrypoint: ``python -m superlogica_download_map``.

Execução canônica (a partir do diretório ``scripts/SELECT``, que contém o pacote)::

    uv run python -m superlogica_download_map --work-dir downloads/fases

O ``--work-dir`` aponta para onde estão ``credentials.json`` e onde as saídas
(``mapa_download.csv`` etc.) serão gravadas; o padrão é o diretório atual.
"""

from superlogica_download_map.cli import app

if __name__ == "__main__":
    app()
