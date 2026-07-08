#!/bin/bash
set -e
cd /service/backend
source venv/bin/activate
pip install -r requirements.txt -q
PID_FILE=django.pid
[ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null || true
python manage.py check
nohup gunicorn -w 2 -b 0.0.0.0:8000 --timeout 120 "config.wsgi:application" > django.log 2>&1 &
echo $! > "$PID_FILE"
echo "Django started, PID=$(cat "$PID_FILE")"
