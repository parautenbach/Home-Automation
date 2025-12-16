#!/bin/bash
set -euo pipefail

# -------------------------------------------------
# Load shared Docker / Home Assistant configuration
# -------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/docker_conf_ha.sh"

docker run $DOCKER_RUN_ARGS "$IMAGE:$TAG_LATEST"
