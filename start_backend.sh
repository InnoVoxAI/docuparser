#!/bin/bash

# 1. Define o diretório onde o .env e o script estão localizados
DIR_ATUAL="/docuparser"

# 2. Carrega as variáveis do arquivo .env deste diretório
if [ -f "$DIR_ATUAL/.env" ]; then
    export $(grep -v '^#' "$DIR_ATUAL/.env" | xargs)
fi

# 3. Configura os caminhos do Python
export PYTHONPATH="/docuparser/docuparse-project/contracts:/docuparser/docuparse-project/shared"

# 4. Diretório onde os PIDs dos serviços em background são registrados
# (usado pelo stop_backend.sh para encerrar os processos depois)
RUN_DIR="/docuparser/.run"
mkdir -p "$RUN_DIR"
rm -f "$RUN_DIR"/*.pid

# 5. Roda a migração da base de dados ANTES de subir qualquer serviço.
# backend-com, backend-ocr e langextract-service não têm banco próprio:
# todos dependem do schema gerenciado pelo backend-core (Django). Por
# isso a migração roda de forma síncrona e bloqueante aqui, para que
# nenhum serviço suba antes do schema estar pronto.
cd /docuparser/docuparse-project/backend-core || exit 1
uv run manage.py migrate && uv run manage.py seed_data
if [ $? -ne 0 ]; then
    echo "Migração falhou. Abortando start_backend.sh." >&2
    exit 1
fi

# 6. Executa o backend-com
cd /docuparser/docuparse-project/backend-com
setsid uv run uvicorn api.app:app --host 0.0.0.0 --port 8070 &
echo $! > "$RUN_DIR/backend-com.pid"

# 7. Executa o backend-core
cd /docuparser/docuparse-project/backend-core
setsid uv run manage.py runserver 0.0.0.0:8000 &
echo $! > "$RUN_DIR/backend-core.pid"

# 8. Executa o backend-ocr
cd /docuparser/docuparse-project/backend-ocr
setsid uv run uvicorn api.app:app --host 0.0.0.0 --port 8080 &
echo $! > "$RUN_DIR/backend-ocr.pid"

# 9. Executa o langextract-service
cd /docuparser/docuparse-project/langextract-service
setsid uv run uvicorn api.app:app --host 0.0.0.0 --port 8091 &
echo $! > "$RUN_DIR/langextract-service.pid"
