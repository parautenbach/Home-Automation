# source/credit:
# https://gist.github.com/ov1d1u/8e6ec1f0a087d1f410c65f16217273ba
# because of this bug/deficiency:
# https://github.com/home-assistant/iOS/issues/1903

import time
import requests
import atomacos

from multiprocessing import Pool

def run(mic_state_prev):
    control_center = atomacos.getAppRefByBundleId('com.apple.controlcenter')
    ha_api_url = "http://<host>:<port>/api/webhook/gaia_audio_input_in_use_alt"

    # these two calls leak memory (40MB -> 500MB in a few hours)
    elems = [elem for elem in control_center.findAllR() if 'AXDescription' in elem.getAttributes()]
    descs = [elem for elem in elems if 'Microphone' in elem.AXDescription.split() and 'use' in elem.AXDescription.split()]
    # True if list isn't empty
    mic_state = bool(descs)
    # print('On' if mic_state else 'Off')

    if mic_state != mic_state_prev:
        # print('State changed')
        try:
            response = requests.put(ha_api_url, data=[('status', 'on' if mic_state else 'off')])
            # print(response.status_code)
        except Exception as e:
            # print(e)
            pass

    return mic_state

if __name__ == '__main__':
    mic_state_prev = False

    with Pool(processes=1) as pool:
        while True:
            mic_state_prev = pool.apply(run, args=(mic_state_prev,))
            time.sleep(3)
