#!/bin/bash
# usage: sync_status.sh [git diff options], e.g. no options for --stat, or -- for the full diff

set -euo pipefail

source "$(git rev-parse --show-toplevel)/scripts/helpers/sync_common.sh"

if [ ! -d "${LAST}" ]; then
    echo "Nothing synced yet."
    exit 1
fi

echo "Last synced: $(cat "${SYNCED_AT}")"

snapshot

cd "${SYNC_DIR}"
if git diff --no-index --quiet last local; then
    echo "In sync."
else
    git diff --no-index "${@:---stat}" last local || true
fi
