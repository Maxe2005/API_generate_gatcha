#!/usr/bin/env bash
set -euo pipefail

revision="${1:-head}"

python -m alembic upgrade "$revision"
