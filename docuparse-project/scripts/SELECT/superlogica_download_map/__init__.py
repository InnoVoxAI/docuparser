"""Fase A — Extração e geração do mapa de download.

Utilitário de linha de comando que descobre, a partir de PDFs-lista de despesas
armazenados em pastas do Google Drive, todos os arquivos a serem baixados na
Fase B, classifica cada um por categoria e grava um ``mapa_download.csv``
incremental e idempotente. **Não baixa** os arquivos-alvo (isso é a Fase B).

Ver ``docs/specs/012-download-map-extraction/`` para spec, plano e contratos.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
