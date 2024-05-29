#!/bin/bash

# 1. go to https://odp-cctegis.opendata.arcgis.com/.
# 2. go to "all data sets".
# 3. search for "dam".
# 4. pick "dam levels".
# 5. it should take you here: https://odp-cctegis.opendata.arcgis.com/datasets/afddd5afd6f948edb35b9be669343fca/explore.
# 6. in the bottom left corner, click "i want to use this".
# 7. click on "open in arcgis online".
# 8. a new tab should open and take you here: # https://www.arcgis.com/home/item.html?id=afddd5afd6f948edb35b9be669343fca
# 9. click the image icon that says download.
# /usr/bin/wget https://www.arcgis.com/sharing/rest/content/items/fc2bbde9663d4a18a1b9fc3c6a38a0da/data -O /home/homeassistant/.homeassistant/downloads/latest_dam_levels.zip
# /usr/bin/unzip -o -d /home/homeassistant/.homeassistant/downloads/ /home/homeassistant/.homeassistant/downloads/latest_dam_levels.zip
# /usr/bin/cat "/home/homeassistant/.homeassistant/downloads/Dam levels 2012 to 2024.csv" | /usr/bin/tail -n 10 | /usr/bin/awk '!/,,,/{line=$0} END{print line}' - > /home/homeassistant/.homeassistant/downloads/latest_dam_levels.csv
/usr/bin/curl -sL https://www.arcgis.com/sharing/rest/content/items/fc2bbde9663d4a18a1b9fc3c6a38a0da/data | /usr/bin/funzip | /usr/bin/tail -n 10 | /usr/bin/awk '!/,,,/{line=$0} END{print line}' > /home/homeassistant/.homeassistant/downloads/latest_dam_levels.csv
