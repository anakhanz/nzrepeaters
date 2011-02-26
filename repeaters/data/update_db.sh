#!/bin/bash

URL_PATH=" http://www.rsm.govt.nz/cms/pdf-library/resource-library//spectrum-search-lite"
URL_FILE="spectrum-search-lite-database"

DB_MDB="prism.mdb"
DB_SQLITE="prism.sqlite"

wget ${URL_PATH}/${URL_FILE}
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
