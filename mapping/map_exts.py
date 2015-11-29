#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Topo50 map data generator
## URLs: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2010, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## Reads map data for the NZ Topo 50 map series from an xl sheet and
## generates a python data file for inclusion in other sources
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.

filename = 'topo50.py'

import csv

sheets = {}

for row in csv.reader(open("topo50-sheet-names-2008.csv")):
    sheets[row[0]] = {'name':row[1],
                      'min_easting':int(row[2]),
                      'max_easting':int(row[3]),
                      'min_northing':int(row[4]),
                      'max_northing':int(row[5]),}


limit_east_min = {}
limit_east_max = {}
limit_north_min = {}
limit_north_max = {}

sheet_codes = list(sheets.keys())
sheet_codes.sort()
for code in sheet_codes:
    if len(code) == 4 and code[0:2] != 'CI':
        north_code = code[0:2]
        east_code = code[2:4]
        limit_east_min[east_code] = sheets[code]['min_easting']
        limit_east_max[east_code] = sheets[code]['max_easting']
        limit_north_min[north_code] = sheets[code]['min_northing']
        limit_north_max[north_code] = sheets[code]['max_northing']

output = """#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Topo50 map data
## URLs: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2010, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## This is data detailing the New Zealand Topo 50 maps and their extents
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
output += """
# Map Shete details #
# ================= #
"""
output += 'maps = {\n'
for code in sheet_codes:
    sheet = sheets[code]
    sheet_txt = "'%s': {" %code
    sheet_txt += """'name':"%s",""" % sheet['name']
    sheet_txt += "'min_easting':%i," % sheet['min_easting']
    sheet_txt += "'max_easting':%i," % sheet['max_easting']
    sheet_txt += "'min_northing':%i," % sheet['min_northing']
    sheet_txt += "'max_northing':%i},\n" % sheet['max_northing']
    output += '        ' + sheet_txt
output += '         }'

output += """
# Eastings Extents #
# ================ #
"""
east_codes = list(limit_east_min.keys())
east_codes.sort()
east_min = "east_min = {\n"
east_max = "east_max = {\n"
for code in east_codes:
    east_min += "             '%s': %i,\n" % (code, limit_east_min[code])
    east_max += "             '%s': %i,\n" % (code, limit_east_max[code])
east_min += "             }\n"
east_max += "             }\n"
output += east_min + east_max

output += """
# Nothings Extents #
# ================ #
"""
north_codes = list(limit_north_min.keys())
north_codes.sort(reverse=True)
north_min = "north_min = {\n"
north_max = "north_max = {\n"
for code in north_codes:
    north_min += "             '%s': %i,\n" % (code, limit_north_min[code])
    north_max += "             '%s': %i,\n" % (code, limit_north_max[code])
north_min += "             }\n"
north_max += "             }\n"
output += north_min + north_max

f = open(filename,'w')
f.write(output)
f.close()