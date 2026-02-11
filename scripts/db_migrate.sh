#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"message for migration\""
  exit 1
fi

message="$1"

python -m alembic revision -m "$message" --autogenerate
