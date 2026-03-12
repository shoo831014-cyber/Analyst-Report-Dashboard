#!/bin/sh
set -eu

mkdir -p data/exports data/snapshots data/logs

alembic upgrade head

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers
