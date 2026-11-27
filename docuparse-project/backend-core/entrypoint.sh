#!/bin/sh
# Entrypoint da imagem do backend-core.
#
#   entrypoint.sh web      (padrão) sobe o gunicorn
#   entrypoint.sh release  migrations (public e tenants) + seed_data, e sai
#   entrypoint.sh worker [args]  worker da fila durável (manage.py run_worker [args])
#   entrypoint.sh <cmd>    executa <cmd> (ex.: uv run python manage.py shell)
#
# `release` deve rodar uma vez por deploy, antes do `web`: no compose é o serviço
# backend-core-release; no k8s, um initContainer ou Job. Enquanto o k8s não tem
# isso, DOCUPARSE_MIGRATE_ON_BOOT=true (padrão) faz o `web` rodar o `release`
# antes de subir, como o CMD antigo fazia. Desligue quando o release estiver fora.
set -e

release() {
    echo "[entrypoint] Applying public schema migrations..."
    uv run --frozen python manage.py migrate_schemas --shared

    # Tenant schemas must be provisioned BEFORE seeding: seed_data writes
    # per-tenant rows inside schema_context(<tenant>). If a tenant schema exists
    # but is empty, those writes fall through search_path to stale
    # public.documents_* tables and fail.
    echo "[entrypoint] Applying tenant schema migrations..."
    uv run --frozen python manage.py migrate_schemas

    echo "[entrypoint] Seeding default tenant, admin user, and permissions..."
    uv run --frozen python manage.py seed_data
}

case "${1:-web}" in
    release)
        release
        ;;
    web)
        case "$(echo "${DOCUPARSE_MIGRATE_ON_BOOT:-true}" | tr '[:upper:]' '[:lower:]')" in
            1 | true | yes) release ;;
        esac
        # 1 worker de propósito: o processamento de documentos roda num
        # ThreadPoolExecutor em memória (documents/services/processing_queue.py),
        # e cada worker do gunicorn criaria o próprio pool. Escalar com threads até
        # existir a fila durável (fase 2 da revisão de arquitetura). Flags extras
        # (ex.: --reload no compose) via GUNICORN_CMD_ARGS, lida pelo gunicorn.
        echo "[entrypoint] Starting gunicorn..."
        exec uv run --frozen gunicorn core.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers 1 \
            --threads "${GUNICORN_THREADS:-4}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile -
        ;;
    worker)
        # Fila durável (fase 2). Não roda migrations: espera a tabela, que o
        # `release` cria. Args extras vão para o run_worker (ex.: --concurrency 4).
        shift
        echo "[entrypoint] Starting queue worker..."
        exec uv run --frozen python manage.py run_worker "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
