#!/bin/bash

#rsync -Pvrm -e "ssh -i ~/.ssh/id_rsa_securitypi" --include='*.yaml' --include='*/' --exclude='*' ${SRC}/. pi@securitypi.local:/tmp/home_assistant
#rsync -Pvrm -e "ssh -i ~/.ssh/id_rsa_homeassistant" --include='*.yaml' --include='*/' --exclude='*' ${SRC}/. homeassistant@homeassistant.local:/tmp/home_assistant
#scp -i ~/.ssh/id_rsa_securitypi -r             *.yaml pi@securitypi.local:/tmp/home_assistant
#scp -i ~/.ssh/id_rsa_securitypi -r ui-lovelace/*.yaml pi@securitypi.local:/tmp/home_assistant/ui-lovelace

set -euo pipefail

source "$(git rev-parse --show-toplevel)/scripts/helpers/sync_common.sh"

snapshot

deleted=$(comm -23 <(list_files "${LAST}") <(list_files "${LOCAL}"))

# --delete keeps staging a mirror; .deleted is excluded by the filters, so it survives
rsync -Pvrmt --delete -e "ssh" "${FILTERS[@]}" "${LOCAL}/." "${REMOTE}"

# appended, so deletions from several syncs survive until sync_config.sh applies them
if [ -n "${deleted}" ]; then
    echo "Deleted since last sync:"
    echo "${deleted}"
    echo "${deleted}" | ssh homeassistant "cat >> /tmp/home_assistant/.deleted"
fi

rsync -rtm --delete "${LOCAL}/." "${LAST}/"
date "+%Y-%m-%d %H:%M:%S" > "${SYNCED_AT}"
