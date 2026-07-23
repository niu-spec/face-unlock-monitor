#!/usr/bin/env bash
set -euo pipefail

# Restart MediaMTX for OBS RTMP ingest and Django/OpenCV RTSP reading.
# Do not bind host port 8888 because BaoTa panel commonly uses it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-lib.sh
source "$SCRIPT_DIR/deploy-lib.sh"

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  if deploy_use_sudo && command -v sudo >/dev/null 2>&1; then
    docker_cmd=(sudo -n docker)
  fi
fi

"${docker_cmd[@]}" rm -f home-mediamtx 2>/dev/null || true

PUBLIC_HOST="${PUBLIC_HOST:-127.0.0.1}"

"${docker_cmd[@]}" run -d \
  --name home-mediamtx \
  --restart=always \
  -p 9090:1935 \
  -p 8554:8554 \
  -p 8889:8889 \
  -p 8189:8189/udp \
  -e "MTX_WEBRTCADDITIONALHOSTS=${PUBLIC_HOST}" \
  bluenviron/mediamtx:latest

"${docker_cmd[@]}" ps | grep home-mediamtx
ss -lntp 2>/dev/null | grep -E "9090|8554|8889" || true
