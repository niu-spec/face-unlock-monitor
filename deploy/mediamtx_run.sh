#!/usr/bin/env bash
set -euo pipefail

# Ensure MediaMTX is running for OBS RTMP ingest and Django/OpenCV RTSP reading.
# Do not bind host port 8888 because BaoTa commonly uses it.

CONTAINER_NAME="${MEDIAMTX_CONTAINER_NAME:-home-mediamtx}"
IMAGE="${MEDIAMTX_IMAGE:-bluenviron/mediamtx:latest}"

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "$CONTAINER_NAME already running"
else
  docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart=always \
    -p 9090:1935 \
    -p 8554:8554 \
    "$IMAGE"
fi

docker ps --filter "name=$CONTAINER_NAME"
ss -lntp | grep -E "(:9090|:8554)" || true
