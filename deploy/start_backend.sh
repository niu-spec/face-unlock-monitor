#!/usr/bin/env bash
set -euo pipefail

# Start backend in foreground for systemd.
# Prefer Django/Gunicorn; fall back to Flask app.py through Gunicorn during migration.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="${BACKEND_DIR:-$REPO_ROOT/backend}"
if [ ! -d "$BACKEND_DIR" ] && [ -d /service/backend ]; then
  BACKEND_DIR=/service/backend
fi

BIND_ADDR="${BACKEND_BIND:-127.0.0.1:8010}"
WORKERS="${GUNICORN_WORKERS:-1}"
THREADS="${GUNICORN_THREADS:-8}"
WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gthread}"
TIMEOUT="${GUNICORN_TIMEOUT:-300}"
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
  exec gunicorn -w "$WORKERS" \
    --worker-class "$WORKER_CLASS" \
    --threads "$THREADS" \
    -b "$BIND_ADDR" \
    --timeout "$TIMEOUT" \
    "config.wsgi:application"
fi

if [ -f app.py ]; then
  exec gunicorn -w "$WORKERS" \
    --worker-class "$WORKER_CLASS" \
    --threads "$THREADS" \
    -b "$BIND_ADDR" \
    --timeout "$TIMEOUT" \
    "app:app"
fi

echo "No Django manage.py or Flask app.py found in $BACKEND_DIR" >&2
exit 1
