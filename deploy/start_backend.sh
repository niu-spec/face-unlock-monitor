#!/usr/bin/env bash
set -euo pipefail

# Start backend in foreground for systemd.
# Prefer Django/Gunicorn; fall back to Flask app.py through Gunicorn during migration.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="${BACKEND_DIR:-$REPO_ROOT/backend}"
if [ ! -d "$BACKEND_DIR" ] && [ -d /service/home-camera-monitor/backend ]; then
  BACKEND_DIR=/service/home-camera-monitor/backend
fi

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
BIND_ADDR="${BACKEND_BIND:-$BACKEND_HOST:$BACKEND_PORT}"
WORKERS="${WORKERS:-1}"
THREADS="${THREADS:-16}"
TIMEOUT="${TIMEOUT:-300}"
DB_ENV_FILE="${DB_ENV_FILE:-/root/home_camera_monitor_db.env}"

if [ -f "$DB_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$DB_ENV_FILE"
  set +a
fi

cd "$BACKEND_DIR"

if [ -d venv ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
elif [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ "${INSTALL_REQUIREMENTS:-0}" = "1" ] && [ -f requirements.txt ]; then
  pip install -r requirements.txt -q
fi

if [ -f manage.py ]; then
  python manage.py check
  exec python3 -m gunicorn config.wsgi:application \
    --workers "$WORKERS" \
    --threads "$THREADS" \
    --bind "$BIND_ADDR" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile -
fi

if [ -f app.py ]; then
  exec python3 -m gunicorn app:app \
    --workers "$WORKERS" \
    --threads "$THREADS" \
    --bind "$BIND_ADDR" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile -
fi

echo "No Django manage.py or Flask app.py found in $BACKEND_DIR" >&2
exit 1
