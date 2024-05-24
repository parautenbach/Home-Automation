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
/usr/bin/curl -s --request GET --url "https://www.arcgis.com/sharing/rest/content/items/afddd5afd6f948edb35b9be669343fca/data" | tail -n 10 | awk '!/,,,/{line=$0} END{print line}' - > /home/homeassistant/.homeassistant/downloads/latest_dam_levels.csv
