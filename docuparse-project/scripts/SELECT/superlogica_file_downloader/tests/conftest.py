"""Torna os pacotes ``superlogica_file_downloader`` e ``superlogica_download_map``
importáveis nos testes.

Insere o diretório ``scripts/SELECT`` (pai dos dois pacotes) no ``sys.path``, para
que os imports funcionem independentemente do diretório de onde o pytest roda.
"""

import pathlib
import sys

_SELECT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(_SELECT_DIR) not in sys.path:
    sys.path.insert(0, str(_SELECT_DIR))
