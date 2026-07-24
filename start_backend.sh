#!/bin/bash

# 1. Define o diretório onde o .env e o script estão localizados
DIR_ATUAL="/docuparser"

# 2. Carrega as variáveis do arquivo .env deste diretório
if [ -f "$DIR_ATUAL/.env" ]; then
    export $(grep -v '^#' "$DIR_ATUAL/.env" | xargs)
fi

# 3. Configura os caminhos do Python
export PYTHONPATH="/docuparser/docuparse-project/contracts:/docuparser/docuparse-project/shared"

# 5. Executa o backend-com
cd /docuparser/docuparse-project/backend-com
uv run uvicorn api.app:app --host 0.0.0.0 --port 8070

# 6. Executa o backend-core
cd /docuparser/docuparse-project/backend-core
uv run manage.py migrate && uv run manage.py seed_data && uv run manage.py runserver 0.0.0.0:8000

# 7. Executa o backend-ocr
cd /docuparser/docuparse-project/backend-ocr
uv run uvicorn api.app:app --host 0.0.0.0 --port 8080

# 8. Executa o langextract-service
cd /docuparser/docuparse-project/langextract-service
uv run uvicorn api.app:app --host 0.0.0.0 --port 8091
