#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

env_value() {
  local value
  value=$(awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' .env)
  value=${value#\'}
  value=${value%\'}
  printf '%s' "$value"
}

POSTGRES_PASSWORD=$(env_value POSTGRES_PASSWORD)
REDIS_PASSWORD=$(env_value REDIS_PASSWORD)
POSTGRES_BIN="$ROOT_DIR/.runtime/postgres/usr/lib/postgresql/16/bin"
POSTGRES_DATA="$ROOT_DIR/.runtime/data/postgres"
REDIS_BIN="$ROOT_DIR/.runtime/redis/usr/bin"
REDIS_LIB="$ROOT_DIR/.runtime/redis/usr/lib/x86_64-linux-gnu"

mkdir -p .runtime/logs .runtime/pids

if ! "$POSTGRES_BIN/pg_ctl" -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
  "$POSTGRES_BIN/pg_ctl" -D "$POSTGRES_DATA" -l "$ROOT_DIR/.runtime/logs/postgres.log" -o "-h 127.0.0.1 -p 5432 -k $POSTGRES_DATA" start
fi

if ! PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_BIN/psql" -h 127.0.0.1 -U iit -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'iit_academic'" | grep -q 1; then
  PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_BIN/createdb" -h 127.0.0.1 -U iit iit_academic
fi

if ! REDISCLI_AUTH="$REDIS_PASSWORD" LD_LIBRARY_PATH="$REDIS_LIB" "$REDIS_BIN/redis-cli" -h 127.0.0.1 ping >/dev/null 2>&1; then
  LD_LIBRARY_PATH="$REDIS_LIB" "$REDIS_BIN/redis-server" --daemonize yes --bind 127.0.0.1 --port 6379 --requirepass "$REDIS_PASSWORD" --dir "$ROOT_DIR/.runtime/data/redis" --pidfile "$ROOT_DIR/.runtime/pids/redis.pid" --logfile "$ROOT_DIR/.runtime/logs/redis.log" --appendonly yes
fi

POSTGRES_USER=iit POSTGRES_PASSWORD="$POSTGRES_PASSWORD" POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 POSTGRES_DB=iit_academic PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head

start_session() {
  local name=$1
  local directory=$2
  local command=$3
  if ! tmux has-session -t "$name" 2>/dev/null; then
    tmux new-session -d -s "$name" -c "$directory" "$command"
  fi
}

start_session nau-chroma "$ROOT_DIR" "exec env ANONYMIZED_TELEMETRY=FALSE backend/.venv/bin/chroma run --path '$ROOT_DIR/.runtime/data/chroma' --host 127.0.0.1 --port 8001 >> '$ROOT_DIR/.runtime/logs/chroma.log' 2>&1"
start_session nau-inference "$ROOT_DIR" "exec env PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 backend/.inference-venv/bin/uvicorn app.infrastructure.inference.server:app --host 127.0.0.1 --port 8010 --workers 1 --no-access-log >> '$ROOT_DIR/.runtime/logs/inference.log' 2>&1"
start_session nau-worker "$ROOT_DIR" "exec env PYTHONPATH=backend ANONYMIZED_TELEMETRY=FALSE backend/.venv/bin/python -m app.workers.rag_worker >> '$ROOT_DIR/.runtime/logs/worker.log' 2>&1"
start_session nau-backend "$ROOT_DIR" "exec env PYTHONPATH=backend ANONYMIZED_TELEMETRY=FALSE backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >> '$ROOT_DIR/.runtime/logs/backend.log' 2>&1"
start_session nau-frontend "$ROOT_DIR/frontend" "exec npm run preview -- --host 0.0.0.0 --port 5173 >> '$ROOT_DIR/.runtime/logs/frontend.log' 2>&1"

printf 'Services lancés. Vérifiez avec: scripts/local-status.sh\n'
