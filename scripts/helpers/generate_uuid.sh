#!/bin/bash
# alt: uuidgen | tr '[:upper:]' '[:lower:]'

# use uuid4 to create random automation ids
python -c 'import uuid; print(uuid.uuid4())'
