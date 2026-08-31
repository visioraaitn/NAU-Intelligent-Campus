#!/usr/bin/env bash
set -u

check_json() {
  local name=$1
  local url=$2
  if response=$(curl --silent --max-time 3 "$url"); then
    printf '%-12s OK %s\n' "$name" "$response"
  else
    printf '%-12s INDISPONIBLE\n' "$name"
  fi
}

if curl --fail --silent --output /dev/null --max-time 3 http://127.0.0.1:5173/; then
  printf '%-12s OK\n' frontend
else
  printf '%-12s INDISPONIBLE\n' frontend
fi

check_json backend http://127.0.0.1:8000/health
check_json readiness http://127.0.0.1:8000/health/ready
check_json inference http://127.0.0.1:8010/health
check_json chroma http://127.0.0.1:8001/api/v2/heartbeat
