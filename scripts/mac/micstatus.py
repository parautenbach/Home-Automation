# source/credit:
# https://gist.github.com/ov1d1u/8e6ec1f0a087d1f410c65f16217273ba
# because of this bug/deficiency:
# https://github.com/home-assistant/iOS/issues/1903
# plist commands:
# https://davidhamann.de/2018/03/13/setting-up-a-launchagent-macos-cron/

import time
import requests
import atomacos

CONTROL_CENTER = atomacos.getAppRefByBundleId('com.apple.controlcenter')
HA_API_URL = "http://<host>:<port>/api/webhook/gaia_audio_input_in_use_alt"

mic_status = False

with open('/tmp/micstatus.txt', 'r') as f:
    mic_status_prev = f.read().strip().lower() == 'true'

elems = [elem for elem in CONTROL_CENTER.findAllR() if 'AXDescription' in elem.getAttributes()]
descs = [elem for elem in elems if 'Microphone' in elem.AXDescription.split() and 'use' in elem.AXDescription.split()]

# True if list isn't empty
mic_status = bool(descs)
# print('On' if mic_status else 'Off')

if mic_status != mic_status_prev:
    # print('State changed')
    try:
        requests.put(HA_API_URL, data=[('status', 'on' if mic_status else 'off')])
        # print(response.status_code)
    except Exception as e:
        # print(e)
        pass

    with open('/tmp/micstatus.txt', 'w') as f:
        f.write(str(mic_status).lower())
