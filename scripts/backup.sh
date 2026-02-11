#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${BACKUP_DIR:-$ROOT_DIR/backups}"
BACKUP_NAME="${BACKUP_NAME:-$(date +%Y%m%d_%H%M%S)}"
BACKUP_PATH="$BACKUP_ROOT/$BACKUP_NAME"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gatcha_postgres}"
POSTGRES_USER="${POSTGRES_USER:-gatcha_user}"
POSTGRES_DB="${POSTGRES_DB:-gatcha_db}"

MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-admin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-password123}"
MINIO_HOST="${MINIO_HOST:-gatcha_generator_minio}"
MINIO_PORT="${MINIO_PORT:-9000}"
DOCKER_NETWORK="${DOCKER_NETWORK:-gatcha_network}"

mkdir -p "$BACKUP_PATH/postgres" "$BACKUP_PATH/minio"

docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_PATH/postgres/${POSTGRES_DB}.sql"

docker run --rm --network "$DOCKER_NETWORK" \
  -e "MC_HOST_minio=http://${MINIO_ACCESS_KEY}:${MINIO_SECRET_KEY}@${MINIO_HOST}:${MINIO_PORT}" \
  -v "$BACKUP_PATH/minio:/backup" \
  minio/mc mirror --overwrite minio/ /backup

cat > "$BACKUP_PATH/backup_info.txt" <<EOF
timestamp=$BACKUP_NAME
postgres_container=$POSTGRES_CONTAINER
postgres_db=$POSTGRES_DB
minio_host=$MINIO_HOST
minio_port=$MINIO_PORT
EOF

echo "Backup completed: $BACKUP_PATH"
