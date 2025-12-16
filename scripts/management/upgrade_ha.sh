#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# Load shared Docker / Home Assistant configuration
# -------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/docker_conf_ha.sh"

# -------------------------------------------------
# Helpers
# -------------------------------------------------
is_running() {
  docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"
}

get_current_version() {
  docker inspect -f '{{ index .Config.Labels "io.hass.version" }}' \
    "$CONTAINER_NAME" 2>/dev/null || echo "none"
}

get_latest_stable() {
  curl -fsSL https://version.home-assistant.io/stable.json \
    | jq -r '.homeassistant["generic-x86-64"]'
}

# -------------------------------------------------
# Determine target version
# -------------------------------------------------
REQUESTED_VERSION="${1:-}"
CURRENT_VERSION="$(get_current_version)"

# -------------------------------------------------
# Auto-migrate old :stable image
# -------------------------------------------------
if [[ "$CURRENT_VERSION" != "none" ]]; then
    CURRENT_IMAGE="$(docker inspect -f '{{.Image}}' "$CONTAINER_NAME")"
    if [[ "$CURRENT_IMAGE" == "$IMAGE:stable" ]]; then
        echo "ℹ️ Migrating old :stable image to versioned tag $CURRENT_VERSION…"
        docker tag "$IMAGE:stable" "$IMAGE:$CURRENT_VERSION"
    fi
fi

if [[ -z "$REQUESTED_VERSION" ]]; then
  REQUESTED_VERSION="$(get_latest_stable)"
fi

if [[ "$CURRENT_VERSION" == "$REQUESTED_VERSION" ]]; then
  echo "ℹ️  Home Assistant is already running version $CURRENT_VERSION"
  exit 0
fi

if ! docker manifest inspect "$IMAGE:$REQUESTED_VERSION" >/dev/null 2>&1; then
  echo "❌ ERROR: Home Assistant version '$REQUESTED_VERSION' does not exist"
  exit 1
fi

# -------------------------------------------------
# Pull new image first (minimal downtime)
# -------------------------------------------------
echo "⬇️  Pulling Home Assistant $REQUESTED_VERSION…"
nice -n 19 ionice -c3 docker pull "$IMAGE:$REQUESTED_VERSION"

# -------------------------------------------------
# Pre-upgrade summary
# -------------------------------------------------
echo
echo "🚀 Preparing Home Assistant upgrade"
echo "   Current version : $CURRENT_VERSION"
echo "   Target version  : $REQUESTED_VERSION"
echo

# -------------------------------------------------
# Stop container if running and backup config
# -------------------------------------------------
if [[ -d "$HA_CONFIG_DIR" ]]; then
  mkdir -p "$HA_BACKUP_DIR"
  BACKUP_FILE="${HA_BACKUP_DIR}/ha_config_${CURRENT_VERSION}.tgz"

  if is_running; then
    echo "🛑 Stopping Home Assistant for backup…"
    docker stop "$CONTAINER_NAME"
  else
    echo "ℹ️  Home Assistant already stopped"
  fi

  echo "📦 Creating config backup"
  echo "   $BACKUP_FILE"

  sudo nice -n 19 ionice -c3 tar -czpf "$BACKUP_FILE" \
    -C "$(dirname "$HA_CONFIG_DIR")" \
    "$(basename "$HA_CONFIG_DIR")"
else
  echo "⚠️  Config directory not found; skipping backup"
fi

# -------------------------------------------------
# Tag images
# -------------------------------------------------
echo
echo "🏷️  Tagging new image as :latest"
docker tag "$IMAGE:$REQUESTED_VERSION" "$IMAGE:$TAG_LATEST"

if [[ "$CURRENT_VERSION" != "none" ]]; then
  echo "🏷️  Preserving previous version as :previous"
  docker tag "$IMAGE:$CURRENT_VERSION" "$IMAGE:$TAG_PREVIOUS" || true
fi

# -------------------------------------------------
# Replace container
# -------------------------------------------------
echo
echo "🔄 Starting Home Assistant $REQUESTED_VERSION…"

docker rm "$CONTAINER_NAME" 2>/dev/null || true
docker run $DOCKER_RUN_ARGS "$IMAGE:$TAG_LATEST"

echo
echo "✅ Upgrade complete"
echo "   Running version : $REQUESTED_VERSION"
