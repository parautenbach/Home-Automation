#!/usr/bin/env bash

IMAGE="ghcr.io/home-assistant/generic-x86-64-homeassistant"
CONTAINER_NAME="homeassistant"

TAG_LATEST="latest"
TAG_PREVIOUS="previous"

HA_CONFIG_DIR="/root/.homeassistant"
HA_BACKUP_DIR="/root/ha_upgrade_backups"

DOCKER_RUN_ARGS="
-d
--name ${CONTAINER_NAME}
--privileged
--network=host
--restart=unless-stopped
-e TZ=Africa/Johannesburg
-v ${HA_CONFIG_DIR}:/config
-v /mnt/nas:/mnt/nas
-v /root/scripts:/root/scripts:ro
-v /tmp:/tmp
-v /run/dbus:/run/dbus:ro
-v /root/.ssh:/root/.ssh:ro
-v /usr/share/fonts/truetype/dejavu:/usr/share/fonts/truetype/dejavu:ro
-e DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
"
