#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$BASE_DIR/.runtime"

stop_pid_file() {
  local name="$1"
  local pid_file="$RUNTIME_DIR/$name.pid"

  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" || true
      echo "[stop_all] stopped $name (pid $pid)"
    else
      echo "[stop_all] $name already stopped"
    fi
    rm -f "$pid_file"
  else
    echo "[stop_all] no pid file for $name"
  fi
}

stop_pid_file "frontend"
stop_pid_file "backend-core"
stop_pid_file "backend-ocr"