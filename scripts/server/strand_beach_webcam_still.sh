#!/bin/bash
# Capture a still from a YouTube live stream, crop 55px from top, update HA local file camera
# Runs entirely outside the Home Assistant container
# Writes latest still to mounted volume

set -euo pipefail

# --- Configuration ---
STREAM_URL="https://www.youtube.com/watch?v=TJKgvQKVz1I"
FILENAME="strand_beach_webcam_still"
OUTPUT="/root/.homeassistant/www/${FILENAME}.jpg"
TMP="/tmp/${FILENAME}.tmp.jpg"

# Absolute paths to binaries (host installation)
YTDLP="/usr/local/bin/yt-dlp"
FFMPEG="/usr/bin/ffmpeg"

# --- Capture ---
{
    echo "=== $(date) ==="

    # Get direct stream URL
    STREAM=$("$YTDLP" -f b -g "$STREAM_URL")

    # Capture single frame, crop 55px from top, write atomically
    # Force dimensions to fit HA picture entity card
    "$FFMPEG" -y -loglevel error \
        -i "$STREAM" \
        -vf "crop=iw:ih-55:0:55,scale=1920:1080" \
        -frames:v 1 \
        -update 1 \
        "$TMP"

    # Atomic move
    mv "$TMP" "$OUTPUT"

    echo "Capture successful: $OUTPUT"

}
