#!/usr/bin/env bash
set -euo pipefail

revision="${1:--1}"

python -m alembic downgrade "$revision"
