#!/bin/bash
set -e
cd /service/backend
source venv/bin/activate
pip install -r requirements.txt -q
PID_FILE=app.pid
[ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null || true
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 120 "app:app" > app.log 2>&1 &
echo $! > "$PID_FILE"
echo "Flask started, PID=$(cat "$PID_FILE")"
