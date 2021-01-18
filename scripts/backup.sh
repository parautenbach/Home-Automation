#!/bin/bash

# Set your paths below. Script can be run from any folder as long as your the right user and the drive is mounted.
# You can either include or exclude the database, incase you have mysql or simply don't want to backup a big file.
# Do check the storage on your drive.

# Source: https://gist.github.com/riemers/041c6a386a2eab95c55ba3ccaa10e7b0

BACKUP_FOLDER=/mnt/nas/Backups/home_assistant/
BACKUP_FILE=${BACKUP_FOLDER}hass-config_$(date +"%Y%m%d_%H%M%S").zip
BACKUP_LOCATION=/home/homeassistant/.homeassistant
DAYSTOKEEP=0  # set to 0 to keep it forever.

log() {
        if [ "${DEBUG}" == "true" ] || [ "${1}" != "d" ]; then
                echo "[${1}] ${2}"
                if [ "${3}" != "" ]; then
                        exit ${3}
                fi
        fi
}

# guard conditions
# not a mounted file system
if [[ "$(stat --file-system --format=%T $BACKUP_FOLDER)" != 'smb2' ]]; then
        log e "Backup folder not found. Is your drive mounted and does the path exist?" 1
fi
# no location to backup
if [ ! -d "${BACKUP_LOCATION}" ]; then
        log e "Home Assistant folder to back up not found. Is it correct?" 1
fi

# backup
pushd ${BACKUP_LOCATION} >/dev/null
log i "Creating backup"
zip -9 -q -r ${BACKUP_FILE} . -x"home-assistant.db" -x"home-assistant_v2.db" -x"home-assistant.log"
popd >/dev/null
log i "Backup complete: ${BACKUP_FILE}"

# purge
if [ "${DAYSTOKEEP}" = 0 ] ; then
        log i "Keeping all files no prunning set"
else
        log i "Deleting backups older then ${DAYSTOKEEP} day(s)"
        OLDFILES=$(find ${BACKUP_FOLDER} -mindepth 1 -mtime +${DAYSTOKEEP} -delete -print)
        if [ ! -z "${OLDFILES}" ] ; then
                log i "Found the following old files:"
                echo "${OLDFILES}"
        fi
fi

