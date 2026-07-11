#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d frontend/dist ]; then
  echo "Building frontend..."
  (cd frontend && npm install && npm run build)
fi

source .venv/bin/activate
exec uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8420}"
