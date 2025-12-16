#!/bin/bash
cd /srv/homeassistant && source bin/activate && sudo systemctl stop home-assistant@homeassistant.service && pip install --upgrade homeassistant 

