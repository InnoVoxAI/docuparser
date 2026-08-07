#!/bin/bash

# 1. Define o diretório onde o .env e o script estão localizados.
#    Resolvido a partir do próprio script para funcionar tanto no dev container
#    (/docuparser) quanto num clone no host.
DIR_ATUAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Carrega as variáveis do arquivo .env deste diretório
if [ -f "$DIR_ATUAL/.env" ]; then
    export $(grep -v '^#' "$DIR_ATUAL/.env" | xargs)
fi

# 3. Configura os caminhos do Python
export PYTHONPATH="$DIR_ATUAL/docuparse-project/contracts:$DIR_ATUAL/docuparse-project/shared"

# 4. Executa o comando passado pelo usuário, se houver
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
