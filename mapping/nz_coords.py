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

import topo50

from nztm import *

def sheetInfo(s):
    s = s[0:4]
    assert s in topo50.maps.keys()
    details = topo50.maps[s]
    return """Sheet:       %s
Name:        %s
minEasting:  %i
maxEasting:  %i
minNorthing: %i
maxNorthing: %i""" % (s, details['name'],
                      details['min_easting'], details['max_easting'],
                      details['min_northing'], details['max_northing'])

def formatNztm(easting, northing):
    return "%i mE %i mN" % (easting, northing)

def topo50ToNztm(s):
    (sheet, easting, northing) = s.split(' ')
    assert sheet in topo50.maps.keys()
    sheetDetails = topo50.maps[sheet]
    sheetEasting = sheetDetails['min_easting']
    sheetNorthing = sheetDetails['min_northing']
    sheetEasting = sheetEasting - (sheetEasting % 100000)
    sheetNorthing = sheetNorthing - (sheetNorthing % 100000)
    easting = sheetEasting + int(float(easting) * 100)
    northing = sheetNorthing + int(float(northing) * 100)
    return (easting, northing)

def nztmToTopo50(easting, northing, highPrecisioin=False):
    for key in topo50.east_max.keys():
        if easting >= topo50.east_min[key] and easting < topo50.east_max[key]:
            eastSheet = key
            break
    for key in topo50.north_max.keys():
        if northing >= topo50.north_min[key] and northing < topo50.north_max[key]:
            northSheet = key
    easting = float(easting % 100000) / 100.0
    northing = float(northing % 100000) / 100.0
    if highPrecisioin:
        easting = '%0.2f' % easting
        if len(easting) == 4:
            easting = '00' + easting
        elif len(easting) == 5:
            easting = '0' + easting
        northing = '%0.2f' % northing
        if len(northing) == 4:
            northing = '00' + northing
        elif len(northing) == 5:
            northing = '0' + northing
    else:

        easting = '%03.0f' % easting
        northing = '%03.0f' % northing

    return northSheet + eastSheet + ' ' + easting + ' ' + northing


def main():
    inputs = [[1576041.15, 6188574.24],
              [1576542.01, 5515331.05],
              [1307103.22, 4826464.86]]
    for i in inputs:
        e = i[0]
        n = i[1]
        lt, ln = nztm_geod(e, n)
        e1, n1 = geod_nztm(lt,ln)
        print "Input NZTM e,n:  %12.3lf %12.3lf" % (e,n)
        print "Output Lat/Long: %12.6lf %12.6lf" % (degrees(lt), degrees(ln))
        print "Output NZTM e,n: %12.3lf %12.3lf" % (e1,n1)
        print "Difference:      %12.3lf %12.3lf" % (e1-e,n1-n)
        print "Map ref std:     %s" % nztmToTopo50(e,n)
        print "Map ref High:    %s" % nztmToTopo50(e,n,True)
        print ""
        print ""

if __name__ == '__main__':
    main()
