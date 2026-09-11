#!/usr/bin/env bash
set -u
result=0

check_json() {
  local name=$1
  local url=$2
  if response=$(curl --fail --silent --max-time 5 "$url") &&
    python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(data.get("ready") is False or data.get("status") == "not_ready")' <<< "$response"; then
    printf '%-12s OK %s\n' "$name" "$response"
  else
    printf '%-12s INDISPONIBLE\n' "$name"
    result=1
  fi
}

if curl --fail --silent --output /dev/null --max-time 3 http://127.0.0.1:8080/; then
  printf '%-12s OK\n' frontend
else
  printf '%-12s INDISPONIBLE\n' frontend
  result=1
fi

check_json backend http://127.0.0.1:8000/health
check_json readiness http://127.0.0.1:8000/health/ready
check_json inference http://127.0.0.1:8010/health
check_json speech http://127.0.0.1:8011/health
check_json chroma http://127.0.0.1:8001/api/v2/heartbeat
exit "$result"
