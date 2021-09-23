#!/bin/bash

# Make/clean build dir

rm -r build
mkdir build

# build the files
./rpt -qblk build/beacons.kml -z build/beacons.kmz -H build/beacons.html
./rpt -qdlk build/digipeaters.kml -z build/digipeaters.kmz -H build/digipeaters.html
./rpt -qrlk build/repeaters.kml -z build/repeaters.kmz -H build/repeaters.html
./rpt -qalk build/licences.kml -z build/licences.kmz -H build/licences.html
./rpt -qask build/sites.kml -z build/sites.kmz -H build/sites.html
./rpt -qak build/all.kml -z build/all.kmz -H build/all.html -j build/data-gen.js -c build/licences.csv -x build/licences.xlsx

# copy static files
#cp html/data.html build
#cp html/index.html build
#cp html/oms.min.js build
#cp html/repeaters.js build
#cp html/treeview.css build
#cp html/style.css build
cp -r html/* build


#Build files for Br74
mkdir build/74
./rpt -qblB 74 -k build/74/beacons.kml -z build/74/beacons.kmz -H build/74/beacons.html
./rpt -qdlB 74 -k build/74/digipeaters.kml -z build/74/digipeaters.kmz -H build/74/digipeaters.html
./rpt -qrlB 74 -k build/74/repeaters.kml -z build/74/repeaters.kmz -H build/74/repeaters.html
./rpt -qalB 74 -k build/74/licences.kml -z build/74/licences.kmz -H build/74/licences.html
./rpt -qasB 74 -k build/74/sites.kml -z build/74/sites.kmz -H build/74/sites.html
./rpt -qaB 74 -k build/74/all.kml -z build/74/all.kmz -H build/74/all.html -j build/74/data-gen.js -c build/74/licences.csv -x build/74/licences.xlsx
cp -r html/* build/74
mv build/74/live-74.kml build/74/live.kml