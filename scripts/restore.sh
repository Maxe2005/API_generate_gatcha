#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${BACKUP_DIR:-$ROOT_DIR/backups}"

BACKUP_NAME="${1:-${BACKUP_NAME:-}}"
if [[ -z "$BACKUP_NAME" ]]; then
  echo "Usage: BACKUP_NAME=<name> bash scripts/restore.sh [name]"
  exit 1
fi

BACKUP_PATH="$BACKUP_ROOT/$BACKUP_NAME"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gatcha_postgres}"
POSTGRES_USER="${POSTGRES_USER:-gatcha_user}"
POSTGRES_DB="${POSTGRES_DB:-gatcha_db}"

MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-admin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-password123}"
MINIO_HOST="${MINIO_HOST:-gatcha_generator_minio}"
MINIO_PORT="${MINIO_PORT:-9000}"
DOCKER_NETWORK="${DOCKER_NETWORK:-gatcha_network}"

SQL_FILE="$BACKUP_PATH/postgres/${POSTGRES_DB}.sql"
if [[ ! -f "$SQL_FILE" ]]; then
  echo "Postgres backup not found: $SQL_FILE"
  exit 1
fi

docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SQL_FILE"

if [[ -d "$BACKUP_PATH/minio" ]]; then
  MC_ARGS=(--overwrite)
  if [[ "${MINIO_REMOVE:-false}" == "true" ]]; then
    MC_ARGS+=(--remove)
  fi

  docker run --rm --network "$DOCKER_NETWORK" \
    -e "MC_HOST_minio=http://${MINIO_ACCESS_KEY}:${MINIO_SECRET_KEY}@${MINIO_HOST}:${MINIO_PORT}" \
    -v "$BACKUP_PATH/minio:/backup" \
    minio/mc mirror "${MC_ARGS[@]}" /backup minio/
fi

echo "Restore completed from: $BACKUP_PATH"
