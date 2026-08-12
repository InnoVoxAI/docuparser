#!/bin/bash

# Encerra todos os serviços de backend subidos por start_backend.sh.
RUN_DIR="/docuparser/.run"

# Portas usadas pelos serviços (fallback caso os PIDs não sejam encontrados)
declare -A PORTS=(
    [backend-com]=8070
    [backend-core]=8000
    [backend-ocr]=8080
    [langextract-service]=8091
)

for name in "${!PORTS[@]}"; do
    pid_file="$RUN_DIR/$name.pid"
    stopped=false

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "Parando $name (pid $pid)..."
            # start_backend.sh inicia cada serviço com setsid, então o pid
            # registrado é o líder do seu próprio process group: matar o
            # grupo (-pid) também mata os processos filhos (ex: uv -> uvicorn).
            kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null
            stopped=true
        fi
        rm -f "$pid_file"
    fi

    if [ "$stopped" = false ]; then
        port="${PORTS[$name]}"
        if fuser "$port"/tcp >/dev/null 2>&1; then
            echo "Parando $name pela porta $port..."
            fuser -k "$port"/tcp >/dev/null 2>&1
        fi
    fi
done

echo "Backend parado."
