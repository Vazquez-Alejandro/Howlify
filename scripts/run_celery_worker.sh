#!/usr/bin/env bash
set -euo pipefail

CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-2}"

exec celery -A howlify.celery_app worker \
  --loglevel=info \
  --concurrency="$CELERY_CONCURRENCY" \
  --max-tasks-per-child=10
