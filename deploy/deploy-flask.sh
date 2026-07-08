#!/bin/bash
set -e
cd /service/home-camera-monitor/backend
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
nohup python3 -m gunicorn config.wsgi:application --workers 1 --threads 16 --bind 127.0.0.1:8010 --timeout 300 --access-logfile - --error-logfile - > django.log 2>&1 &
echo $! > "$PID_FILE"
echo "Django started, PID=$(cat "$PID_FILE")"
