#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

env_value() {
  awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' .env
}

for session in nau-frontend nau-backend nau-worker nau-inference nau-chroma; do
  tmux kill-session -t "$session" 2>/dev/null || true
done

REDIS_PASSWORD=$(env_value REDIS_PASSWORD)
REDIS_LIB="$ROOT_DIR/.runtime/redis/usr/lib/x86_64-linux-gnu"
REDISCLI_AUTH="$REDIS_PASSWORD" LD_LIBRARY_PATH="$REDIS_LIB" "$ROOT_DIR/.runtime/redis/usr/bin/redis-cli" -h 127.0.0.1 shutdown >/dev/null 2>&1 || true
"$ROOT_DIR/.runtime/postgres/usr/lib/postgresql/16/bin/pg_ctl" -D "$ROOT_DIR/.runtime/data/postgres" stop -m fast >/dev/null 2>&1 || true

printf 'Services locaux arrêtés.\n'
