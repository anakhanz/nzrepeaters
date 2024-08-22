#!/bin/bash

# Script for updating the companion files that are used
# by the nzrepeaters map generation tool

# Requirements:
#    bash
#    zip

# update the version marker file
rm version
date +%d/%m/%Y >> version

mv data.zip data.zip.bak

zip -q data.zip *.csv ${DB_SQLITE}

