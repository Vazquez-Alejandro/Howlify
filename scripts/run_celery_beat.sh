#!/usr/bin/env bash
set -euo pipefail

exec celery -A howlify.celery_app beat \
  --loglevel=info
