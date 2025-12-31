#!/bin/bash

grep -RhoE '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' . | sort | uniq -d | while read -r uuid; do       echo "=== $uuid ==="; grep -Rnw . -e "$uuid"; done
