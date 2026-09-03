#!/bin/sh
set -eu

exec uvicorn app.infrastructure.inference.speech_server:app \
  --host 0.0.0.0 \
  --port 8011 \
  --workers 1 \
  --no-access-log
