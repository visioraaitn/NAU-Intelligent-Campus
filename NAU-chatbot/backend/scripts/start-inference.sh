#!/bin/sh
set -eu

exec uvicorn app.infrastructure.inference.server:app \
  --host 0.0.0.0 \
  --port 8010 \
  --workers 1 \
  --no-access-log

