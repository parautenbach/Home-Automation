#!/bin/bash

/usr/bin/ssh $1 'sudo shutdown -h now'
echo "Shutting down $1"
