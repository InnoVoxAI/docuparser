#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docuparse-project}"
BACKUP_ROOT="${BACKUP_ROOT:-$PROJECT_DIR/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_DIR="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p "$TARGET_DIR"

echo "Writing backup to $TARGET_DIR"

docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$TARGET_DIR/postgres.sql"

backup_volume() {
    local volume_name="$1"
    local archive_name="$2"

    docker run --rm \
        -v "$volume_name:/volume:ro" \
        -v "$TARGET_DIR:/backup" \
        alpine:3.20 \
        tar -czf "/backup/$archive_name" -C /volume .
}

backup_volume "${COMPOSE_PROJECT_NAME}_docuparse-storage" "docuparse-storage.tar.gz"
backup_volume "${COMPOSE_PROJECT_NAME}_docuparse-events" "docuparse-events.tar.gz"
backup_volume "${COMPOSE_PROJECT_NAME}_redis-data" "redis-data.tar.gz"
backup_volume "${COMPOSE_PROJECT_NAME}_minio-data" "minio-data.tar.gz"

cat > "$TARGET_DIR/manifest.txt" <<EOF
created_at=$TIMESTAMP
compose_project=$COMPOSE_PROJECT_NAME
postgres_dump=postgres.sql
storage_archive=docuparse-storage.tar.gz
events_archive=docuparse-events.tar.gz
redis_archive=redis-data.tar.gz
minio_archive=minio-data.tar.gz
EOF

echo "Backup completed: $TARGET_DIR"
