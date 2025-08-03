#!/bin/bash

# this WILL NOT work from within the container (no pg_dump)
# scheduled with a root cronjob

BACKUP_FOLDER=/mnt/nas/Backups/home_assistant_db/
BACKUP_FILE=${BACKUP_FOLDER}homeassistant_$(/usr/bin/date -u +"%Y%m%d_%H%M%S").dump.gz
DAYSTOKEEP=0  # set to 0 to keep it forever.

/usr/bin/echo "[i] Using backup folder: $BACKUP_FOLDER"

log() {
    if [ "${DEBUG}" == "true" ] || [ "${1}" != "d" ]; then
        /usr/bin/echo "[${1}] ${2}"
        if [ "${3}" != "" ]; then
            /usr/bin/exit ${3}
        fi
    fi
}

# guard: check for mounted file system
if [[ "$(/usr/bin/stat --file-system --format=%T $BACKUP_FOLDER)" != "smb2" ]]; then
    log e "Backup folder not found. Is your drive mounted and does the path exist?" 1
fi

# backup
log i "Creating backup"
PGPASSWORD=homeassistant /usr/bin/pg_dump -U homeassistant -h localhost homeassistant | /usr/bin/gzip -9 > "${BACKUP_FILE}"
log i "Backup complete: ${BACKUP_FILE}"

# purge
if [ "${DAYSTOKEEP}" = 0 ]; then
    log i "Keeping all files no pruning set"
else
    log i "Deleting backups older than ${DAYSTOKEEP} day(s)"
    OLDFILES=$(/usr/bin/find ${BACKUP_FOLDER} -mindepth 1 -mtime +${DAYSTOKEEP} -delete -print)
    if [ ! -z "${OLDFILES}" ]; then
        log i "Found the following old files:"
        /usr/bin/echo "${OLDFILES}"
    fi
fi
