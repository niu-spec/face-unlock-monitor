#!/usr/bin/env bash
set -euo pipefail

failures=0
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
DB_PORT="${DB_PORT:-3307}"

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "[OK] $name"
  else
    echo "[FAIL] $name"
    failures=$((failures + 1))
  fi
}

check "MediaMTX container home-mediamtx is running" \
  bash -c "docker ps --filter name=home-mediamtx --filter status=running --format '{{.Names}}' | grep -qx home-mediamtx"

check "RTMP port 9090 is listening" \
  bash -c "ss -lnt | grep -q ':9090'"

check "RTSP port 8554 is listening" \
  bash -c "ss -lnt | grep -q ':8554'"

check "MySQL port $DB_PORT is listening" \
  bash -c "ss -lnt | grep -q ':$DB_PORT'"

check "Backend port $BACKEND_PORT is listening on localhost" \
  bash -c "ss -lnt | grep -q '127.0.0.1:$BACKEND_PORT'"

check "Video status API responds" \
  curl -fsS --max-time 5 "$BACKEND_URL/api/video/status"

check "Stream source API responds" \
  curl -fsS --max-time 5 "$BACKEND_URL/api/video/streams/1/source"

if [ "$failures" -gt 0 ]; then
  echo "$failures check(s) failed"
  exit 1
fi

echo "Stack checks passed"
