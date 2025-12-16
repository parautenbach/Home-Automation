#!/bin/bash

docker restart homeassistant && docker logs -n 10 -f homeassistant
