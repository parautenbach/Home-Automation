#!/bin/bash

# https://www.capetown.gov.za/Family%20and%20home/residential-utility-services/residential-water-and-sanitation-services/this-weeks-dam-levels
# https://web1.capetown.gov.za/web1/opendataportal/DatasetDetail?DatasetName=Dam%20levels
# replaced by: https://odp-cctegis.opendata.arcgis.com/documents/dam-levels/about
# 1. navigate to the above
# 2. click the "open document" button above the summary and to the right of the big blue file icon
# 3. on the next page, click on the file icon to download the latest file and check its contents
# 4. now open the browser's inspector and search the dom for "downloadhandler"
# 5. copy the link and test it in the browser (look out for a incorrectly encoded &amp; between .csv and DatasetDocument and replace it with &)
# 6. replace the link below
/usr/bin/curl -s --request GET --url "https://www.capetown.gov.za/_layouts/OpenDataPortalHandler/DownloadHandler.ashx?DocumentName=Dam+levels+2012+to+2024.csv&DatasetDocument=https%3A%2F%2Fcityapps.capetown.gov.za%2Fsites%2Fopendatacatalog%2FDocuments%2FDam%2520levels%2FDam%2520levels%25202012%2520to%25202024.csv" | tail -n 10 | awk '!/,,,/{line=$0} END{print line}' - > /home/homeassistant/.homeassistant/downloads/latest_dam_levels.csv
