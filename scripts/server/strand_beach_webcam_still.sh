#!/bin/bash
# Capture a still from a YouTube live stream, update HA local file camera
# Runs entirely outside the Home Assistant container
# Writes latest still to mounted volume

set -euo pipefail

# --- Configuration ---
# the stream gets a new video id whenever it restarts, so find the live one by title;
# anchored because the channel also runs a Dakkies Strand beach webcam
CHANNEL_STREAMS="https://www.youtube.com/@KeytoCapeTown/streams"
TITLE_PATTERN="^Strand beach webcam"
FILENAME="strand_beach_webcam_still"
OUTPUT="/root/.homeassistant/www/${FILENAME}.jpg"
TMP="/tmp/${FILENAME}.tmp.jpg"

# Absolute paths to binaries (host installation)
YTDLP="/usr/local/bin/yt-dlp"
FFMPEG="/usr/bin/ffmpeg"
# youtube won't hand out stream urls without a js runtime, and cron's PATH doesn't include deno
DENO="/root/.deno/bin/deno"

# --- Capture ---
{
    echo "=== $(date) ==="

    VIDEO_ID=$("$YTDLP" --js-runtimes "deno:${DENO}" --flat-playlist --playlist-end 10 \
        --match-filter "live_status=is_live & title~='${TITLE_PATTERN}'" \
        --print id "$CHANNEL_STREAMS" | head -n 1 || true)
    if [ -z "$VIDEO_ID" ]; then
        echo "No live stream found"
        exit 1
    fi

    # live streams only offer separate audio and video, and a still needs only video
    STREAM=$("$YTDLP" --js-runtimes "deno:${DENO}" -f bv -g "https://www.youtube.com/watch?v=${VIDEO_ID}")

    # Capture single frame, write atomically
    # Force dimensions to fit HA picture entity card
    "$FFMPEG" -y -loglevel error \
        -i "$STREAM" \
        -vf "scale=1920:1080" \
        -frames:v 1 \
        -update 1 \
        "$TMP"

    # Atomic move
    mv "$TMP" "$OUTPUT"

    echo "Capture successful: $OUTPUT"

}
