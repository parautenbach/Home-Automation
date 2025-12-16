#!/bin/bash

# from within docker container
cp `ls -t /config/www/gallery/$1/$2_*.jpg | head -1` /config/www/$2_last.jpg

