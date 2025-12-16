#!/bin/bash

# CONFIG
STREAM_URL="rtsp://securitypi:8554/unicast"
# HA will time out after 60 sec!
DURATION="00:00:50"  # hh:mm:ss
OUTPUT_DIR="/tmp"
FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ENTITY_ID="camera.security_camera"

# Generate timestamped filename: camera.security_camera_20250802-213118.mp4
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
OUTPUT_FILE="${OUTPUT_DIR}/${ENTITY_ID}_${TIMESTAMP}.mp4"

# Run ffmpeg
ffmpeg \
  -rtsp_transport tcp -i "$STREAM_URL" \
  -vf "drawtext=fontfile=${FONT_PATH}:text='%{localtime\:%Y-%m-%d %T}':x=w-text_w-10:y=10:fontsize=24:fontcolor=white@0.8:borderw=2:bordercolor=black@1:box=0" \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -b:a 128k \
  -t "$DURATION" \
  -y "$OUTPUT_FILE"

