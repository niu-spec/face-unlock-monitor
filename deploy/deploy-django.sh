#!/bin/bash
# Deploy Django backend on Linux (production)
# Requires: conda env home-camera OR venv with dlib installed
set -e
cd /service/backend

if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate home-camera
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/anaconda3/etc/profile.d/conda.sh"
  conda activate home-camera
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "No conda env home-camera or venv found."
  exit 1
fi

pip install -r requirements.txt -q
PID_FILE=django.pid
[ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null || true
python manage.py check
nohup gunicorn -w 2 -b 0.0.0.0:8000 --timeout 120 "config.wsgi:application" > django.log 2>&1 &
echo $! > "$PID_FILE"
echo "Django started on :8000, PID=$(cat "$PID_FILE")"
