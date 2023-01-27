#!/bin/bash

# https://www.capetown.gov.za/Family%20and%20home/residential-utility-services/residential-water-and-sanitation-services/this-weeks-dam-levels
# https://web1.capetown.gov.za/web1/opendataportal/DatasetDetail?DatasetName=Dam%20levels
# replaced by: https://odp-cctegis.opendata.arcgis.com/documents/dam-levels/about
/usr/bin/curl -s --request GET --url "https://www.capetown.gov.za/_layouts/OpenDataPortalHandler/DownloadHandler.ashx?DocumentName=Dam+levels+2012+to+2023.csv&DatasetDocument=https%3A%2F%2Fcityapps.capetown.gov.za%2Fsites%2Fopendatacatalog%2FDocuments%2FDam%2520levels%2FDam%2520levels%25202012%2520to%25202023.csv" | tail -n 1 > /home/homeassistant/.homeassistant/downloads/latest_dam_levels.csv
