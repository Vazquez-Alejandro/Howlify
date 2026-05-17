#!/bin/bash
# Default mode is now "api" (React SPA served by FastAPI).
# Set HOWLIFY_MODE=web to use legacy Streamlit UI.
MODE="${HOWLIFY_MODE:-api}"

if [ "$MODE" = "api" ]; then
    echo "[howlify] Starting API server..."
    exec python -m uvicorn howlify.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
elif [ "$MODE" = "worker" ]; then
    echo "[howlify] Starting Celery worker..."
    exec celery -A howlify.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
elif [ "$MODE" = "beat" ]; then
    echo "[howlify] Starting Celery beat..."
    exec celery -A howlify.celery_app beat --loglevel=info
elif [ "$MODE" = "worker-beat" ]; then
    echo "[howlify] Starting Celery worker + beat (dev mode)..."
    exec celery -A howlify.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}" --beat
elif [ "$MODE" = "legacy-worker" ]; then
    echo "[howlify] Starting legacy worker..."
    exec python -m engine.worker
else
    echo "[howlify] Starting web (Streamlit)..."
    python scripts/telegram_connect.py &
    exec streamlit run app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0
fi
