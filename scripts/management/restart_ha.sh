#!/bin/bash

docker restart -t 300 homeassistant && docker logs -n 10 -f homeassistant
