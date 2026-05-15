#!/bin/bash
MODE="${HOWLIFY_MODE:-web}"

if [ "$MODE" = "api" ]; then
    echo "[howlify] Starting API server..."
    exec python -m uvicorn howlify.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
elif [ "$MODE" = "worker" ]; then
    echo "[howlify] Starting worker..."
    exec python -m engine.worker
else
    echo "[howlify] Starting web (Streamlit)..."
    python scripts/telegram_connect.py &
    exec streamlit run app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0
fi
