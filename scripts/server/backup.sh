#!/bin/sh

# Paths
BACKUP_FOLDER=/mnt/nas/Backups/home_assistant/
BACKUP_FILE="${BACKUP_FOLDER}hass-config_$(date -u +"%Y%m%d_%H%M%S").tar.gz"
BACKUP_LOCATION=/config  # Adjusted for the Docker mount
DAYSTOKEEP=0  # Set to 0 to keep backups forever

# Logging function
log() {
    LEVEL=$1
    MESSAGE=$2
    EXITCODE=$3

    if [ "$DEBUG" = "true" ] || [ "$LEVEL" != "d" ]; then
        echo "[$LEVEL] $MESSAGE"
        if [ -n "$EXITCODE" ]; then
            exit "$EXITCODE"
        fi
    fi
}

# Guard: backup folder exists and is writable
if [ ! -d "$BACKUP_FOLDER" ] || [ ! -w "$BACKUP_FOLDER" ]; then
    log e "Backup folder not found or not writable. Is your drive mounted and path correct?" 1
fi

# Guard: backup source exists
if [ ! -d "$BACKUP_LOCATION" ]; then
    log e "Home Assistant folder to back up not found. Is the path correct?" 1
fi

# Backup process
cd "$BACKUP_LOCATION" || log e "Failed to enter backup location." 1
log i "Creating backup..."
tar --exclude="home-assistant.db" \
    --exclude="home-assistant_v2.db" \
    --exclude="home-assistant.log" \
    -czf "$BACKUP_FILE" .
log i "Backup complete: $BACKUP_FILE"

# Purge old backups
if [ "$DAYSTOKEEP" -eq 0 ]; then
    log i "Keeping all files; no pruning set."
else
    log i "Deleting backups older than $DAYSTOKEEP day(s)..."
    OLDFILES=$(find "$BACKUP_FOLDER" -mindepth 1 -mtime +"$DAYSTOKEEP" -delete -print)
    if [ -n "$OLDFILES" ]; then
        log i "Deleted the following old files:"
        echo "$OLDFILES"
    fi
fi

