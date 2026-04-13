#!/usr/bin/env bash
set -euo pipefail

# Simple local launcher for:
# - backend-ocr (FastAPI) on :8001
# - backend-core (Django) on :8000
# - frontend (Vite) on :5173

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCR_DIR="$BASE_DIR/backend-ocr"
CORE_DIR="$BASE_DIR/backend-core"
FRONT_DIR="$BASE_DIR/frontend"
RUNTIME_DIR="$BASE_DIR/.runtime"

mkdir -p "$RUNTIME_DIR"

log() { echo "[run_all] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1"
    exit 1
  }
}

start_backend_ocr() {
  log "Starting backend-ocr..."
  cd "$OCR_DIR"

  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt
  else
    source .venv/bin/activate
  fi

  nohup .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8001 \
    > "$RUNTIME_DIR/backend-ocr.log" 2>&1 &
  echo $! > "$RUNTIME_DIR/backend-ocr.pid"
  deactivate || true
}

start_backend_core() {
  log "Starting backend-core..."
  cd "$CORE_DIR"

  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt
  else
    source .venv/bin/activate
  fi

  export OCR_API_BASE_URL="http://127.0.0.1:8001"
  .venv/bin/python manage.py migrate >/dev/null 2>&1 || true

  nohup env OCR_API_BASE_URL="$OCR_API_BASE_URL" \
    .venv/bin/python manage.py runserver 0.0.0.0:8000 \
    > "$RUNTIME_DIR/backend-core.log" 2>&1 &
  echo $! > "$RUNTIME_DIR/backend-core.pid"
  deactivate || true
}

start_frontend() {
  log "Starting frontend..."
  cd "$FRONT_DIR"

  if [[ ! -d "node_modules" ]]; then
    npm install
  fi

  nohup npm run dev -- --host 0.0.0.0 --port 5173 \
    > "$RUNTIME_DIR/frontend.log" 2>&1 &
  echo $! > "$RUNTIME_DIR/frontend.pid"
}

healthcheck() {
  log "Waiting services..."
  sleep 3

  set +e
  curl -fsS http://127.0.0.1:8001/engines >/dev/null
  OCR_OK=$?
  curl -fsS http://127.0.0.1:8000/api/ocr/engines >/dev/null
  CORE_OK=$?
  curl -fsS http://127.0.0.1:5173 >/dev/null
  FRONT_OK=$?
  set -e

  echo
  echo "=== Service status ==="
  [[ $OCR_OK -eq 0 ]] && echo "backend-ocr : OK (http://127.0.0.1:8001)" || echo "backend-ocr : FAIL"
  [[ $CORE_OK -eq 0 ]] && echo "backend-core: OK (http://127.0.0.1:8000)" || echo "backend-core: FAIL"
  [[ $FRONT_OK -eq 0 ]] && echo "frontend    : OK (http://127.0.0.1:5173)" || echo "frontend    : FAIL"
  echo
  echo "Open UI: http://127.0.0.1:5173"
  echo "Logs: $RUNTIME_DIR/*.log"
}

main() {
  require_cmd python3
  require_cmd npm
  require_cmd curl

  start_backend_ocr
  start_backend_core
  start_frontend
  healthcheck
}

main "$@"