#!/bin/sh
# Старт приложения: при первом запуске строит поисковый индекс по PDF.
set -e

DATA_DIR="${DATA_DIR:-/app/data}"
MANUALS_DIR="${MANUALS_DIR:-/app/manuals}"

if [ ! -f "$DATA_DIR/index/bm25.pkl" ]; then
  echo "[entrypoint] индекс не найден — собираю из $MANUALS_DIR"
  python /app/backend/scripts/ingest.py
fi

exec uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8090
