"""Leitura de variáveis de ambiente para o settings.py."""

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool = False) -> bool:
    """Lê uma variável de ambiente como booleano.

    Só "1", "true", "yes" e "on" (sem diferenciar maiúsculas) contam como
    verdadeiro. Qualquer outro valor, inclusive "False" e a string vazia, é
    falso. Sem a variável, vale `default`.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES
