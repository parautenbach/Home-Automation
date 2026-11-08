#!/bin/bash

chown -R root:root /tmp/home_assistant/
cp -vR /tmp/home_assistant/* /root/.homeassistant/

# files deleted locally, listed by sync_to_server.sh
if [ -f /tmp/home_assistant/.deleted ]; then
    sort -u /tmp/home_assistant/.deleted | while IFS= read -r f; do
        case "${f}" in
            ""|/*|*..*) echo "Skipping unsafe path: ${f}" ;;
            *)
                if [ -e "/root/.homeassistant/${f}" ]; then
                    rm -iv "/root/.homeassistant/${f}" < /dev/tty
                fi
                ;;
        esac
    done
    rm -f /tmp/home_assistant/.deleted
fi

chown -R home_assistant:home_assistant /tmp/home_assistant/
