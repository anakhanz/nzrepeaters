#!/bin/bash

URL_PATH=" http://www.rsm.govt.nz/cms/pdf-library/resource-library//spectrum-search-lite"
URL_FILE="spectrum-search-lite-database"

DB_MDB="prism.mdb"
DB_SQLITE="prism.sqlite"

wget ${URL_PATH}/${URL_FILE} -O ${URL_FILE}
unzip ${URL_FILE}

mv ${DB_SQLITE} ${DB_SQLITE}.bak

mdb-schema ${DB_MDB}| perl -wpe 's%^DROP TABLE %DROP TABLE IF EXISTS %i;
  s%(Memo/Hyperlink|DateTime( \(Short\))?)%TEXT%i;
  s%(Boolean|Byte|Byte|Numeric|Replication ID|(\w+ )?Integer)%INTEGER%i;
  s%(BINARY|OLE|Unknown ([0-9a-fx]+)?)%BLOB%i;
  s%\s*\(\d+\)\s*(,?[ \t]*)$%${1}%;' | sqlite3 ${DB_SQLITE}
for i in $(mdb-tables ${DB_MDB}); do echo $i; (
  echo "BEGIN TRANSACTION;";
  MDB_JET3_CHARSET=cp1256 mdb-export -R ";\n" -I ${DB_MDB} $i;
  echo "END TRANSACTION;" ) | sed 's/ *"/\"/g' | sqlite3 ${DB_SQLITE}; done

rm ${URL_FILE}
rm ${DB_MDB}

sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS associatedlicences;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS emission;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS emissionlimit;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS issuingoffice;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS licenceconditions;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS licencetype;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS managementright;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS mapdistrict;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS radiationpattern;'
sqlite3 ${DB_SQLITE} 'DROP TABLE IF EXISTS receiveconfiguration;'
sqlite3 ${DB_SQLITE} 'DELETE FROM licence WHERE licencetype NOT LIKE "Amateur%";'
sqlite3 ${DB_SQLITE} 'DELETE FROM clientname WHERE clientid NOT IN (SELECT DISTINCT clientid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM spectrum WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM transmitconfiguration WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM spectrum WHERE licenceid NOT IN (SELECT DISTINCT licenceid FROM licence);'
sqlite3 ${DB_SQLITE} 'DELETE FROM location WHERE locationid NOT IN (SELECT DISTINCT locationid FROM transmitconfiguration);'
sqlite3 ${DB_SQLITE} 'DELETE FROM geographicreference WHERE locationid NOT IN (SELECT DISTINCT locationid FROM transmitconfiguration);'
sqlite3 ${DB_SQLITE} 'VACUUM'

rm version
date +%d/%m/%Y >> version
