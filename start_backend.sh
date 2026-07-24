#!/bin/bash

# 1. Define o diretório onde o .env e o script estão localizados
DIR_ATUAL="/docuparser"

# 2. Carrega as variáveis do arquivo .env deste diretório
if [ -f "$DIR_ATUAL/.env" ]; then
    export $(grep -v '^#' "$DIR_ATUAL/.env" | xargs)
fi

# 3. Configura os caminhos do Python
export PYTHONPATH="/docuparser/docuparse-project/contracts:/docuparser/docuparse-project/shared"

# 4. Entra no diretório onde o comando uvicorn precisa rodar
cd /docuparser/docuparse-project/backend-com

# 5. Executa o backend-com
uv run uvicorn api.app:app --host 0.0.0.0 --port 8070
