#!/bin/bash

# https://unix.stackexchange.com/questions/2161/rsync-filter-copying-one-pattern-only
#rsync -Pvrm -e "ssh -i ~/.ssh/id_rsa_securitypi" --include='*.yaml' --include='*/' --exclude='*' /Users/parautenbach/Github/Home-Automation/home_assistant/. pi@securitypi.local:/tmp/home_assistant

rsync -Pvrm -e "ssh" --include='*.yaml' --include='*.csv' --include='*.jinja' --include='*/' --exclude='*' /Users/parautenbach/Github/Home-Automation/home_assistant/. homeassistant:/tmp/home_assistant

#rsync -Pvrm -e "ssh -i ~/.ssh/id_rsa_homeassistant" --include='*.yaml' --include='*/' --exclude='*' /Users/parautenbach/Github/Home-Automation/home_assistant/. homeassistant@homeassistant.local:/tmp/home_assistant

#scp -i ~/.ssh/id_rsa_securitypi -r             *.yaml pi@securitypi.local:/tmp/home_assistant
#scp -i ~/.ssh/id_rsa_securitypi -r ui-lovelace/*.yaml pi@securitypi.local:/tmp/home_assistant/ui-lovelace
