#!/usr/bin/env bash
set -e

# Restart MediaMTX for OBS RTMP ingest and Django/OpenCV RTSP reading.
# Do not bind host port 8888 because BaoTa panel commonly uses it.

docker rm -f home-mediamtx 2>/dev/null || true

docker run -d \
  --name home-mediamtx \
  --restart=always \
  -p 9090:1935 \
  -p 8554:8554 \
  -p 8889:8889 \
  -p 8189:8189/udp \
  -e MTX_WEBRTCADDITIONALHOSTS=152.136.29.158 \
  bluenviron/mediamtx:latest

docker ps | grep home-mediamtx
ss -lntp | grep -E "9090|8554|8889" || true
