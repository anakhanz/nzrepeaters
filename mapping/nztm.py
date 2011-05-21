#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Topo50 map data generator
## URLs: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2010, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## Converts coordinates between the New Zealand Transverse Merctator and
## latitude and longitude on the New Zealand Geodetic Datum 2000
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

from math import radians, degrees
from tm import tmprojection, tm_geod, geod_tm

NZTM_A  = 6378137.0
NZTM_RF = 298.257222101

NZTM_CM =     173.0
NZTM_OLAT =     0.0
NZTM_SF =       0.9996
NZTM_FE =     1600000.0
NZTM_FN =     10000000.0

def get_nztm_projectoion():
    ''''
    Define NZTM Projection parameters
    '''
    return tmprojection(NZTM_A, NZTM_RF, radians(NZTM_CM), NZTM_SF, radians(NZTM_OLAT),
                        NZTM_FE, NZTM_FN, 1.0)

nztm = get_nztm_projectoion()

def nztm_geod(e, n):
    '''
    Wrapper function to convert from NZTM to latitude and longitude.

    Arguments:
    ce - input easting (metres)
    cn - input northing (metres)

    Returns
    lt - output latitude (radians)
    ln - output longitude (radians)
    '''
    return tm_geod(nztm, e, n)

def geod_nztm(lt, ln):
    '''
    Wrapper function to convert from latitude and longitude to NZTM.

    Arguments:
    lt - input latitude (radians)
    ln - input longitude (radians)

    Returns:
    ce - output easting  (metres)
    cn - output northing (metres)
    '''
    return geod_tm(nztm, lt, ln)

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
        print ""
        print ""

if __name__ == '__main__':
    main()