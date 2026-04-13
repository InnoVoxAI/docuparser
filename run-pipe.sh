#!/usr/bin/env bash
set -euo pipefail

# Simple local launcher for:
# - backend-ocr (FastAPI) on :8001
# - backend-core (Django) on :8000
# - frontend (Vite) on :5173

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_project_root() {
  if [[ -d "$BASE_DIR/backend-ocr" && -d "$BASE_DIR/backend-core" && -d "$BASE_DIR/frontend" ]]; then
    echo "$BASE_DIR"
    return
  fi

  if [[ -d "$BASE_DIR/docuparse-project/backend-ocr" && -d "$BASE_DIR/docuparse-project/backend-core" && -d "$BASE_DIR/docuparse-project/frontend" ]]; then
    echo "$BASE_DIR/docuparse-project"
    return
  fi

  echo ""
}

PROJECT_ROOT="$(resolve_project_root)"
if [[ -z "$PROJECT_ROOT" ]]; then
  echo "Could not find backend-ocr, backend-core and frontend folders."
  echo "Expected either:"
  echo "  - $BASE_DIR/{backend-ocr,backend-core,frontend}"
  echo "  - $BASE_DIR/docuparse-project/{backend-ocr,backend-core,frontend}"
  exit 1
fi

OCR_DIR="$PROJECT_ROOT/backend-ocr"
CORE_DIR="$PROJECT_ROOT/backend-core"
FRONT_DIR="$PROJECT_ROOT/frontend"
RUNTIME_DIR="$BASE_DIR/.runtime"

mkdir -p "$RUNTIME_DIR"

log() { echo "[run_all] $*"; }

FRONT_SKIPPED=0
FRONT_SKIP_REASON=""

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1"
    exit 1
  }
}

kill_port_if_busy() {
  local port="$1"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "$port"/tcp 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -ltnp "sport = :$port" 2>/dev/null | awk -F'pid=' 'NR>1{split($2,a,","); if(a[1] ~ /^[0-9]+$/) print a[1]}' || true)"
  fi

  if [[ -n "${pids// /}" ]]; then
    log "Port $port busy, stopping process(es): $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    kill -9 $pids 2>/dev/null || true
  fi
}

wait_http_ok() {
  local url="$1"
  local attempts="${2:-20}"
  local delay="${3:-1}"
  local i

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done

  return 1
}

can_start_frontend() {
  local node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"

  if [[ "$node_major" -lt 18 ]]; then
    FRONT_SKIPPED=1
    FRONT_SKIP_REASON="Node $(node -v 2>/dev/null || echo unknown) is not supported by Vite 5 (requires >=18)."
    return 1
  fi

  return 0
}

start_backend_ocr() {
  log "Starting backend-ocr..."
  kill_port_if_busy 8001
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
  kill_port_if_busy 8000
  cd "$CORE_DIR"

  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt
  else
    source .venv/bin/activate
  fi

  export BACKEND_OCR_URL="http://127.0.0.1:8001"
  export OCR_API_BASE_URL="$BACKEND_OCR_URL"
  .venv/bin/python manage.py migrate >/dev/null 2>&1 || true

  nohup env BACKEND_OCR_URL="$BACKEND_OCR_URL" OCR_API_BASE_URL="$OCR_API_BASE_URL" \
    .venv/bin/python manage.py runserver 0.0.0.0:8000 \
    > "$RUNTIME_DIR/backend-core.log" 2>&1 &
  echo $! > "$RUNTIME_DIR/backend-core.pid"
  deactivate || true
}

start_frontend() {
  if ! can_start_frontend; then
    log "Skipping frontend: $FRONT_SKIP_REASON"
    return 0
  fi

  log "Starting frontend..."
  kill_port_if_busy 5173
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
  set +e
  wait_http_ok http://127.0.0.1:8001/engines 30 1
  OCR_OK=$?
  wait_http_ok http://127.0.0.1:8000/api/ocr/engines 30 1
  CORE_OK=$?
  if [[ $FRONT_SKIPPED -eq 1 ]]; then
    FRONT_OK=2
  else
    wait_http_ok http://127.0.0.1:5173 30 1
    FRONT_OK=$?
  fi
  set -e

  echo
  echo "=== Service status ==="
  [[ $OCR_OK -eq 0 ]] && echo "backend-ocr : OK (http://127.0.0.1:8001)" || echo "backend-ocr : FAIL"
  [[ $CORE_OK -eq 0 ]] && echo "backend-core: OK (http://127.0.0.1:8000)" || echo "backend-core: FAIL"
  if [[ $FRONT_OK -eq 0 ]]; then
    echo "frontend    : OK (http://127.0.0.1:5173)"
  elif [[ $FRONT_OK -eq 2 ]]; then
    echo "frontend    : SKIPPED ($FRONT_SKIP_REASON)"
  else
    echo "frontend    : FAIL"
  fi
  echo
  if [[ $FRONT_SKIPPED -eq 0 ]]; then
    echo "Open UI: http://127.0.0.1:5173"
  else
    echo "Frontend disabled due to Node version. Upgrade Node to >=18 and rerun."
  fi
  echo "Logs: $RUNTIME_DIR/*.log"
}

main() {
  require_cmd python3
  require_cmd node
  require_cmd npm
  require_cmd curl

  start_backend_ocr
  start_backend_core
  start_frontend
  healthcheck
}

main "$@"