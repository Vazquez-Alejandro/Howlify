#!/bin/bash
# Howlify — modos de ejecución:
#   api       → FastAPI + React SPA (default)
#   worker    → Celery worker (procesa tareas de scraping)
#   beat      → Celery beat (scheduler de tareas)
#   worker-beat → Celery worker + beat juntos (dev mode)
MODE="${HOWLIFY_MODE:-api}"

case "$MODE" in
    api)
        echo "[howlify] Starting API server..."
        exec python -m uvicorn howlify.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
        ;;
    worker)
        echo "[howlify] Starting Celery worker..."
        exec celery -A howlify.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;
    beat)
        echo "[howlify] Starting Celery beat..."
        exec celery -A howlify.celery_app beat --loglevel=info
        ;;
    worker-beat)
        echo "[howlify] Starting Celery worker + beat (dev mode)..."
        exec celery -A howlify.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}" --beat
        ;;
    *)
        echo "[howlify] Modo desconocido: $MODE"
        echo "Usar: api, worker, beat, o worker-beat"
        exit 1
        ;;
esac
