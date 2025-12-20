#!/bin/bash

chown -R root:root /tmp/home_assistant/
cp -vR /tmp/home_assistant/* /root/.homeassistant/
chown -R home_assistant:home_assistant /tmp/home_assistant/
