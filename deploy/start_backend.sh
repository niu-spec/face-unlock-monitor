#!/usr/bin/env bash
# Start video/AI backend via gunicorn (used by systemd home-camera-backend.service).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

BIND="${BACKEND_BIND:-127.0.0.1:8010}"
WORKERS="${WORKERS:-1}"
THREADS="${THREADS:-16}"
TIMEOUT="${TIMEOUT:-300}"

if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
elif command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate "${CONDA_ENV_NAME:-home-camera}"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV_NAME:-home-camera}"
else
  echo "No venv or conda env found for backend" >&2
  exit 1
fi

exec gunicorn config.wsgi:application \
  --bind "$BIND" \
  --workers "$WORKERS" \
  --threads "$THREADS" \
  --timeout "$TIMEOUT" \
  --access-logfile - \
  --error-logfile -
