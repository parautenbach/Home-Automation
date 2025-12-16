#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# Load shared Docker/HA configuration
# -------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/docker_conf_ha.sh"

# -------------------------------------------------
# Parse arguments
# -------------------------------------------------
RESTORE_CONFIG=false
if [[ "${1:-}" == "--restore-config" ]]; then
  RESTORE_CONFIG=true
fi

# -------------------------------------------------
# Sanity checks
# -------------------------------------------------
if ! docker image inspect "$IMAGE:$TAG_PREVIOUS" >/dev/null 2>&1; then
  echo "❌ ERROR: No previous Home Assistant image available to roll back to."
  exit 1
fi

PREVIOUS_VERSION="$(docker inspect -f '{{ index .Config.Labels "io.hass.version" }}' \
  "$IMAGE:$TAG_PREVIOUS")"

# -------------------------------------------------
# Pre-rollback summary
# -------------------------------------------------
echo "↩️  Preparing Home Assistant rollback"
echo "   Target version : $PREVIOUS_VERSION"
echo

# -------------------------------------------------
# Stop container
# -------------------------------------------------
echo "🛑 Stopping Home Assistant…"
docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true

# -------------------------------------------------
# Optional config restore
# -------------------------------------------------
if $RESTORE_CONFIG; then
  BACKUP_FILE="${HA_BACKUP_DIR}/ha_config_${PREVIOUS_VERSION}.tgz"

  echo
  echo "📦 Restoring Home Assistant config"
  echo "   Source: $BACKUP_FILE"

  if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "❌ ERROR: Backup file not found."
    exit 1
  fi

  tar -xzpf "$BACKUP_FILE" -C /
else
  echo
  echo "ℹ️  Config restore skipped (image rollback only)"
fi

# -------------------------------------------------
# Roll back image
# -------------------------------------------------
echo
echo "🏷️  Re-tagging :previous as :latest"
docker tag "$IMAGE:$TAG_PREVIOUS" "$IMAGE:$TAG_LATEST"

# -------------------------------------------------
# Restart container
# -------------------------------------------------
echo
echo "🔄 Starting Home Assistant $PREVIOUS_VERSION…"
docker run $DOCKER_RUN_ARGS "$IMAGE:$TAG_LATEST"

echo
echo "✅ Rollback complete"
echo "   Running version : $PREVIOUS_VERSION"
