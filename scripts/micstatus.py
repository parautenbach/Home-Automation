# source/credit:
# https://gist.github.com/ov1d1u/8e6ec1f0a087d1f410c65f16217273ba
# because of this bug/deficiency:
# https://github.com/home-assistant/iOS/issues/1903

import time
import requests
import atomacos

CONTROL_CENTER = atomacos.getAppRefByBundleId('com.apple.controlcenter')
HA_API_URL = "http://<host>:<port>/api/webhook/gaia_audio_input_in_use_alt"

mic_state = False
mic_state_prev = False

while True:
    elems = [elem for elem in CONTROL_CENTER.findAllR() if 'AXDescription' in elem.getAttributes()]
    descs = [elem for elem in elems if 'Microphone' in elem.AXDescription.split() and 'use' in elem.AXDescription.split()]
    # print(descs)
    # True if list isn't empty
    mic_state = bool(descs)

    if mic_state != mic_state_prev:
        try:
            requests.put(HA_API_URL, data=[('status', 'on' if mic_state else 'off')])
        except:
            pass
        mic_state_prev = mic_state
    time.sleep(1)
