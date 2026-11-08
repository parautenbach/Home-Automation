# sourced by sync_to_server.sh and sync_status.sh

REPO="$(git rev-parse --show-toplevel)"
SRC="${REPO}/home_assistant"
SYNC_DIR="${REPO}/.sync"
LAST="${SYNC_DIR}/last"
LOCAL="${SYNC_DIR}/local"
SYNCED_AT="${SYNC_DIR}/synced_at"
REMOTE="homeassistant:/tmp/home_assistant"

# https://unix.stackexchange.com/questions/2161/rsync-filter-copying-one-pattern-only
FILTERS=(--include='*.yaml' --include='*.csv' --include='*.jinja' --include='*/' --exclude='*')

# filtered copy of the working tree, as it would be synced
snapshot() {
    mkdir -p "${LOCAL}"
    rsync -rtm --delete "${FILTERS[@]}" "${SRC}/." "${LOCAL}/"
}

list_files() {
    [ -d "$1" ] || return 0
    (cd "$1" && find . -type f | sed 's|^\./||' | LC_ALL=C sort)
}
