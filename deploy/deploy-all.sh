#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DEPLOY_PATH:-/service/home-camera-monitor}"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
ENV_FILE="${DJANGO_ENV_FILE:-$BACKEND_DIR/.env.production}"
DJANGO_SERVICE="${DJANGO_SERVICE:-home-camera-backend}"
MEDIA_SCRIPT="$APP_DIR/deploy/mediamtx_run.sh"

echo "[deploy] app dir: $APP_DIR"

cd "$APP_DIR"
if [ "${SKIP_GIT_UPDATE:-0}" = "1" ]; then
  echo "[deploy] skip git update"
else
  DEPLOY_BRANCH="${DEPLOY_BRANCH:-dev}"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[deploy] working tree has local changes; commit/stash them or set SKIP_GIT_UPDATE=1" >&2
    git status --short >&2
    exit 1
  fi
  git fetch origin "$DEPLOY_BRANCH"
  git checkout "$DEPLOY_BRANCH"
  git pull --ff-only origin "$DEPLOY_BRANCH"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy] missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

cd "$BACKEND_DIR"
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate "${CONDA_ENV_NAME:-home-camera}"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV_NAME:-home-camera}"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/anaconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV_NAME:-home-camera}"
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "[deploy] no conda env or venv found for backend" >&2
  exit 1
fi

python manage.py migrate --noinput
python manage.py check

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files "$DJANGO_SERVICE.service" --no-legend | grep -q "^$DJANGO_SERVICE.service"; then
  systemctl restart "$DJANGO_SERVICE"
else
  echo "[deploy] systemd service not found, falling back to deploy-django.sh"
  bash "$APP_DIR/deploy/deploy-django.sh"
fi

cd "$FRONTEND_DIR"
npm ci
npm run build

if command -v docker >/dev/null 2>&1; then
  bash "$MEDIA_SCRIPT"
else
  echo "[deploy] docker not found, skip MediaMTX restart"
fi

if command -v nginx >/dev/null 2>&1; then
  nginx -t
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet nginx; then
    systemctl reload nginx
  else
    nginx -s reload
  fi
else
  echo "[deploy] nginx not found, skip reload"
fi

echo "[deploy] completed"
