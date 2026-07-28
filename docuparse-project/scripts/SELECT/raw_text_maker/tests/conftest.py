"""Torna o pacote ``raw_text_maker`` importável nos testes.

Insere o diretório ``scripts/SELECT`` (pai do pacote) no ``sys.path``, para que os
imports funcionem independentemente do diretório de onde o pytest roda — mesmo
padrão já usado pelos pacotes das Fases A e B.
"""

import pathlib
import sys

_SELECT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(_SELECT_DIR) not in sys.path:
    sys.path.insert(0, str(_SELECT_DIR))
