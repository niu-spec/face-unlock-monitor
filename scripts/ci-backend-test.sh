#!/usr/bin/env bash
# Shared backend CI entry — used by Jenkins and GitHub Actions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

export CI="${CI:-true}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-ci-test-secret-key}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

# GitHub Actions 直接使用 setup-python 提供的解释器，避免重复创建 venv。
if [ -n "${GITHUB_ACTIONS:-}" ]; then
  pip install -q --upgrade pip
  pip install -q -r requirements-ci.txt
else
  VENV_DIR="${CI_VENV_DIR:-$ROOT/backend/.venv-ci}"
  if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  pip install -q --upgrade pip
  pip install -q -r requirements-ci.txt
fi

python manage.py check
python manage.py test \
  apps.face.tests \
  apps.detection.tests \
  apps.video_stream.tests \
  apps.reports.tests \
  --verbosity=2
