"""Torna o pacote ``superlogica_download_map`` importável nos testes.

Insere o diretório ``scripts/SELECT`` (pai do pacote) no ``sys.path``, para que
``import superlogica_download_map.<modulo>`` funcione independentemente do
diretório de onde o pytest é invocado.
"""

import pathlib
import sys

_SELECT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(_SELECT_DIR) not in sys.path:
    sys.path.insert(0, str(_SELECT_DIR))
