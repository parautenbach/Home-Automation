#!/bin/bash
# alt: uuidgen | tr '[:upper:]' '[:lower:]'

# use uuid4 to create random automation ids
uuid=$(python -c 'import uuid; import sys; sys.stdout.write(str(uuid.uuid4()))')
printf "%s" "$uuid" | pbcopy
echo "$uuid"

