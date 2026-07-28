"""Entrypoint: ``python -m raw_text_maker``.

Execução canônica (a partir do diretório ``scripts/SELECT``, que contém o pacote)::

    uv run python -m raw_text_maker

O padrão já aponta para ``downloads/fases/downloads`` (saída da Fase B) e grava
em ``downloads/fases/Raw Text Docs``. Use ``--source-root``/``--output-root``
para apontar outra árvore.
"""

from raw_text_maker.cli import app

if __name__ == "__main__":
    app()
