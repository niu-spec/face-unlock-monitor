#!/bin/bash
set -e
cd /service/backend
source venv/bin/activate
if [ -f /root/home_camera_monitor_db.env ]; then
  set -a
  source /root/home_camera_monitor_db.env
  set +a
fi
pip install -r requirements.txt -q
PID_FILE=django.pid
[ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null || true
python manage.py check
nohup gunicorn -w 1 --worker-class gthread --threads 8 -b 127.0.0.1:8010 --timeout 300 "config.wsgi:application" > django.log 2>&1 &
echo $! > "$PID_FILE"
echo "Django started, PID=$(cat "$PID_FILE")"
