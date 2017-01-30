#!/bin/bash

# Script for converting the NZ Smart database to a for tat can be used
# by the nzrepeaters map generation tool

# Requirements:
#    bash
#    mdb tools
#    perl
#    sed
#    sqlite3
#    wget

# Download URL & file name
#URL_PATH="http://www.rsm.govt.nz/cms/pdf-library/resource-library/spectrum-search-lite/spectrum-search-lite-database"
#URL_FILE="spectrum-search-lite-database.zip"
URL_PATH="http://www.rsm.govt.nz/online-services-resources/pdf-and-documents-library/tools/spectrum-search-lite/prism.zip"
URL_FILE="prism.zip"
# Database file names
DB_MDB="prism.mdb"
DB_SQLITE="prism.sqlite"

NEEDED_TABLES=(licence
               clientname
               emission
               spectrum
               transmitconfiguration
               receiveconfiguration
	           location
               geographicreference)

UNNEEDED_TABLES=(associatedlicences
                 emissionlimit
                 issuingoffice
                 licenceconditions
                 licencetype
                 managementright
                 mapdistrict
                 radiationpattern)

# Get and unzip the source database file
wget -q ${URL_PATH} -O ${URL_FILE}
unzip -qof ${URL_FILE}

# remove zip file
rm ${URL_FILE}

# create backup of destination sqlite file
mv ${DB_SQLITE} ${DB_SQLITE}.bak

# loop through the required tables creating the table and  
for i in ${NEEDED_TABLES[@]}; do
  mdb-schema -T $i ${DB_MDB}| perl -wpe 's%^DROP TABLE %DROP TABLE IF EXISTS %i;
    s%(Memo/Hyperlink|DateTime( \(Short\))?)%TEXT%i;
    s%(Boolean|Byte|Byte|Numeric|Replication ID|(\w+ )?Integer)%INTEGER%i;
    s%(BINARY|OLE|Unknown ([0-9a-fx]+)?)%BLOB%i;
    s%\s*\(\d+\)\s*(,?[ \t]*)$%${1}%;' | sqlite3 ${DB_SQLITE}
  (echo "BEGIN TRANSACTION;";
  MDB_JET3_CHARSET=cp1256 mdb-export -R ";\n" -I mysql ${DB_MDB} $i;
  echo "END TRANSACTION;" ) | sed 's/ *"/\"/g' | sqlite3 ${DB_SQLITE};
done

# Remove the source database file
#rm ${DB_MDB}

# Remove all non Amateur related records from the destination database
sqlite3 ${DB_SQLITE} 'DELETE FROM licence WHERE licencetype NOT LIKE "Amateur%";'
sqlite3 ${DB_SQLITE} 'DELETE FROM clientname WHERE clientid NOT IN (SELECT DISTINCT clientid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM spectrum WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM receiveconfiguration WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM transmitconfiguration WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM spectrum WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM emission WHERE emissionid NOT IN (SELECT DISTINCT emissionid FROM spectrum);'
sqlite3 ${DB_SQLITE} 'DELETE FROM location WHERE locationid NOT IN (SELECT DISTINCT locationid FROM transmitconfiguration);'
sqlite3 ${DB_SQLITE} 'DELETE FROM geographicreference WHERE locationid NOT IN (SELECT DISTINCT locationid FROM transmitconfiguration);'

# Add msissing CARDS clientname record
sqlite3 ${DB_SQLITE} 'INSERT INTO clientname VALUES (129376,"CANTERBURY AMATEUR RADIO DEVELOPMENT SOCIETY INCORPORATED",1,"64 Broadhaven Ave","Parklands","Christchurch");'

# Compact/Vacuul the database
sqlite3 ${DB_SQLITE} 'VACUUM'

# update the version marker file
rm version
date +%d/%m/%Y >> version

mv data.zip data.zip.bak

zip -q data.zip *.csv ${DB_SQLITE}

