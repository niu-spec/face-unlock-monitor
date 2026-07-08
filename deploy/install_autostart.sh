#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo bash deploy/install_autostart.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/service/home-camera-monitor}"

mkdir -p "$INSTALL_ROOT/deploy/systemd"

cp "$SCRIPT_DIR/mediamtx_run.sh" "$INSTALL_ROOT/deploy/mediamtx_run.sh"
cp "$SCRIPT_DIR/start_backend.sh" "$INSTALL_ROOT/deploy/start_backend.sh"
cp "$SCRIPT_DIR/check_stack.sh" "$INSTALL_ROOT/deploy/check_stack.sh"
sed "s|/service/home-camera-monitor|$INSTALL_ROOT|g" "$SCRIPT_DIR/systemd/home-camera-backend.service" \
  > /etc/systemd/system/home-camera-backend.service
sed "s|/service/home-camera-monitor|$INSTALL_ROOT|g" "$SCRIPT_DIR/systemd/home-mediamtx-ensure.service" \
  > /etc/systemd/system/home-mediamtx-ensure.service

chmod +x "$INSTALL_ROOT/deploy/mediamtx_run.sh" \
  "$INSTALL_ROOT/deploy/start_backend.sh" \
  "$INSTALL_ROOT/deploy/check_stack.sh"

if [ "$REPO_ROOT" != "$INSTALL_ROOT" ] && [ -d "$REPO_ROOT/backend" ] && [ ! -e "$INSTALL_ROOT/backend" ]; then
  echo "Note: backend directory is not installed to $INSTALL_ROOT/backend."
  echo "Copy or clone the repository to $INSTALL_ROOT, or set BACKEND_DIR in /etc/systemd/system/home-camera-backend.service."
fi

systemctl daemon-reload
systemctl enable home-mediamtx-ensure.service
systemctl enable home-camera-backend.service

echo "Autostart installed."
echo "Start now with:"
echo "  systemctl restart home-mediamtx-ensure.service"
echo "  systemctl restart home-camera-backend.service"
echo "Check with:"
echo "  $INSTALL_ROOT/deploy/check_stack.sh"
