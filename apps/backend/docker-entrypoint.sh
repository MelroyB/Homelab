#!/usr/bin/env sh
set -eu

echo "[backend] running alembic migrations"
alembic upgrade head

echo "[backend] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
