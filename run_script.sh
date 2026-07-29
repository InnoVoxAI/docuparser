#!/bin/bash

# 1. Define o diretório onde o .env e o script estão localizados
DIR_ATUAL="/docuparser"

# 2. Carrega as variáveis do arquivo .env deste diretório
if [ -f "$DIR_ATUAL/.env" ]; then
    export $(grep -v '^#' "$DIR_ATUAL/.env" | xargs)
fi

# 3. Configura os caminhos do Python
export PYTHONPATH="/docuparser/docuparse-project/contracts:/docuparser/docuparse-project/shared"

# 4. Executa o comando passado pelo usuário, se houver
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
