#!/usr/bin/env bash
set -euo pipefail

# Docker launcher for the full DocuParse stack.
# Builds images and starts:
# - backend-ocr (FastAPI) on :8080
# - backend-core (Django) on :8000
# - frontend (Vite) on :5173

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_project_root() {
  if [[ -f "$BASE_DIR/docker-compose.yml" ]]; then
    echo "$BASE_DIR"
    return
  fi

  if [[ -f "$BASE_DIR/docuparse-project/docker-compose.yml" ]]; then
    echo "$BASE_DIR/docuparse-project"
    return
  fi

  echo ""
}

PROJECT_ROOT="$(resolve_project_root)"
if [[ -z "$PROJECT_ROOT" ]]; then
  echo "Could not find docker-compose.yml."
  echo "Expected either:"
  echo "  - $BASE_DIR/docker-compose.yml"
  echo "  - $BASE_DIR/docuparse-project/docker-compose.yml"
  exit 1
fi

COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

log() { echo "[run-pipe] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1"
    exit 1
  }
}

wait_http_ok() {
  local url="$1"
  local attempts="${2:-30}"
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

healthcheck() {
  log "Waiting for services..."
  set +e
  wait_http_ok http://127.0.0.1:8080/engines 45 1
  OCR_OK=$?
  wait_http_ok http://127.0.0.1:8000/api/ocr/engines 45 1
  CORE_OK=$?
  wait_http_ok http://127.0.0.1:5173 45 1
  FRONT_OK=$?
  set -e

  echo
  echo "=== Service status ==="
  [[ $OCR_OK -eq 0 ]] && echo "backend-ocr : OK (http://127.0.0.1:8080)" || echo "backend-ocr : FAIL"
  [[ $CORE_OK -eq 0 ]] && echo "backend-core: OK (http://127.0.0.1:8000)" || echo "backend-core: FAIL"
  [[ $FRONT_OK -eq 0 ]] && echo "frontend    : OK (http://127.0.0.1:5173)" || echo "frontend    : FAIL"
  echo
  echo "Open UI: http://127.0.0.1:5173"
  echo "API Core: http://127.0.0.1:8000"
  echo "API OCR : http://127.0.0.1:8080"
  echo
  echo "To stop: docker compose -f $COMPOSE_FILE down"
}

check_backend_ocr_deps() {
  log "Checking backend-ocr Python dependencies inside container..."

  local check_cmd
  check_cmd="from importlib import util; required=['fastapi','cv2','pytesseract','pypdfium2','httpx','openai','paddle','paddleocr']; missing=[m for m in required if util.find_spec(m) is None]; print('missing=' + ','.join(missing) if missing else 'all_required_modules_ok')"

  set +e
  $DOCKER_CMD -f "$COMPOSE_FILE" exec -T backend-ocr python -c "$check_cmd"
  local deps_status=$?
  set -e

  if [[ $deps_status -ne 0 ]]; then
    echo "[run-pipe] WARNING: could not validate backend-ocr dependencies in container."
    echo "[run-pipe] Run manually: $DOCKER_CMD -f $COMPOSE_FILE exec backend-ocr python -c \"$check_cmd\""
  fi
}

resolve_docker_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi

  echo ""
}

ensure_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    return
  fi

  log "No .env found in $PROJECT_ROOT. Creating default .env..."
  cat > "$ENV_FILE" <<'EOF'
# Default .env for DocuParse
DEBUG=True
EOF
}

main() {
  require_cmd docker
  require_cmd curl

  DOCKER_CMD="$(resolve_docker_compose_cmd)"
  if [[ -z "$DOCKER_CMD" ]]; then
    echo "Could not find Docker Compose. Install 'docker compose' plugin or 'docker-compose'."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running. Please start Docker and retry."
    exit 1
  fi

  ensure_env_file

  log "Building and starting services with: $DOCKER_CMD"
  cd "$PROJECT_ROOT"
  $DOCKER_CMD -f "$COMPOSE_FILE" up --build -d

  healthcheck
  check_backend_ocr_deps
}

main "$@"