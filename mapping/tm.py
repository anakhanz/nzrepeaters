#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Topo50 map data generator
## URLs: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2010, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## Converts coordinates between the Transverse Merctator and
## latitude and longitude
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

from math import pi, sin, cos, sqrt#, degrees,radians

class tmprojection():
    '''Class used to define the parameters of a TM projection'''
    def __init__(self,a,rf,cm,sf,lto,fe,fn,utom):
        '''
        Constructor
        Arguments:
        a    -
        rf   -
        cm   - Centeral meridan
        sf   - Scale factor
        lto  - Origin latitude
        fe   - False easting
        fn   - False northing
        utom - Unit to metre conversion

        '''
        self.meridian = cm # Centeral meridan
        self.scalef = sf   # Scale factor
        self.orglat = lto  # Origin latitude
        self.falsee = fe   # False easting
        self.falsen = fn   # False northing
        self.utom = utom   # Unit to metre conversion
        # Ellipsoid parameters
        if( rf != 0.0 ):
            f = 1.0/rf
        else:
            f = 0.0
        self.a = a
        self.rf = rf
        self.f = f
        self.e2 = 2.0*f - f*f
        self.ep2 = self.e2/( 1.0 - self.e2 )

        self.om = meridian_arc( self, self.orglat ) # Intermediate calculation

def meridian_arc(tm, lt):
    '''
    Returns the length of meridional arc (Helmert formula)
    Method based on Redfearn's formulation as expressed in GDA technical
    manual at http://www.anzlic.org.au/icsm/gdatm/index.html

    Arguments:
    tm - projection
    lt - latitude (radians)

    Return value is the arc length in metres
    '''
    a = tm.a

    e2 = tm.e2
    e4 = e2*e2
    e6 = e4*e2

    A0 = 1 - (e2/4.0) - (3.0*e4/64.0) - (5.0*e6/256.0)
    A2 = (3.0/8.0) * (e2+e4/4.0+15.0*e6/128.0)
    A4 = (15.0/256.0) * (e4 + 3.0*e6/4.0)
    A6 = 35.0*e6/3072.0

    return  a*(A0*lt-A2*sin(2*lt)+A4*sin(4*lt)-A6*sin(6*lt))

def foot_point_lat(tm, m):
    '''
    Calculates the foot point latitude from the meridional arc
    Method based on Redfearn's formulation as expressed in GDA technical
    manual at http://www.anzlic.org.au/icsm/gdatm/index.html

    Arguments:
    tm - projection (for scale factor)
    m  - meridional arc (metres)

    Returns the foot point latitude (radians)
    '''
    f = tm.f
    a = tm.a

    n  = f/(2.0-f)
    n2 = n*n
    n3 = n2*n
    n4 = n2*n2

    g = a*(1.0-n)*(1.0-n2)*(1.0+9.0*n2/4.0+225.0*n4/64.0)
    sig = m/g

    return (sig + (3.0*n/2.0 - 27.0*n3/32.0)*sin(2.0*sig)
                + (21.0*n2/16.0 - 55.0*n4/32.0)*sin(4.0*sig)
                + (151.0*n3/96.0) * sin(6.0*sig)
                + (1097.0*n4/512.0) * sin(8.0*sig))

def tm_geod(tm,ce,cn):
    '''
    Function to convert from Tranverse Mercator to latitude and longitude.
    Method based on Redfearn's formulation as expressed in GDA technical
    manual at http://www.anzlic.org.au/icsm/gdatm/index.html

    Arguments:
    tm - projection
    ce - input easting (metres)
    cn - input northing (metres)

    Returns
    lt - output latitude (radians)
    ln - output longitude (radians)
    '''
    fn = tm.falsen
    fe = tm.falsee
    sf = tm.scalef
    e2 = tm.e2
    a = tm.a
    cm = tm.meridian
    om = tm.om
    utom = tm.utom

    cn1  =  (cn - fn)*utom/sf + om
    fphi = foot_point_lat(tm, cn1)
    slt = sin(fphi)
    clt = cos(fphi)

    eslt = (1.0-e2*slt*slt)
    eta = a/sqrt(eslt)
    rho = eta * (1.0-e2) / eslt
    psi = eta/rho

    E = (ce-fe)*utom
    x = E/(eta*sf)
    x2 = x*x

    t = slt/clt
    t2 = t*t
    t4 = t2*t2

    trm1 = 1.0/2.0

    trm2 = ((-4.0*psi+9.0*(1-t2))*psi+12.0*t2)/24.0

    trm3 = ((((8.0*(11.0-24.0*t2)*psi
               -12.0*(21.0-71.0*t2))*psi
              +15.0*((15.0*t2-98.0)*t2+15))*psi
             +180.0*((-3.0*t2+5.0)*t2))*psi + 360.0*t4)/720.0

    trm4 = (((1575.0*t2+4095.0)*t2+3633.0)*t2+1385.0)/40320.0

    lt = fphi+(t*x*E/(sf*rho))*(((trm4*x2-trm3)*x2+trm2)*x2-trm1)

    trm1 = 1.0

    trm2 = (psi+2.0*t2)/6.0

    trm3 = (((-4.0*(1.0-6.0*t2)*psi
              +(9.0-68.0*t2))*psi
             +72.0*t2)*psi
            +24.0*t4)/120.0

    trm4 = (((720.0*t2+1320.0)*t2+662.0)*t2+61.0)/5040.0

    ln = cm - (x/clt)*(((trm4*x2-trm3)*x2+trm2)*x2-trm1)

    return (lt, ln)

def geod_tm( tm,lt,ln):
    '''
    Function to convert from latitude and longitude to Transverse Mercator
    Method based on Redfearn's formulation as expressed in GDA technical
    manual at http://www.anzlic.org.au/icsm/gdatm/index.html
    Loosely based on FORTRAN source code by J.Hannah and A.Broadhurst.

    Arguments:
    tm - projection
    lt - input latitude (radians)
    ln - input longitude (radians)

    Returns:
    ce - output easting  (metres)
    cn - output northing (metres)
    '''
    fn = tm.falsen
    fe = tm.falsee
    sf = tm.scalef
    e2 = tm.e2
    a = tm.a
    cm = tm.meridian
    om = tm.om
    utom = tm.utom

    dlon  =  ln - cm
    while dlon > pi:
        dlon -= pi*2.0
    while dlon < -pi:
        dlon += pi*2.0

    m = meridian_arc(tm,lt)

    slt = sin(lt)

    eslt = (1.0-e2*slt*slt)
    eta = a/sqrt(eslt)
    rho = eta * (1.0-e2) / eslt
    psi = eta/rho

    clt = cos(lt)
    w = dlon

    wc = clt*w
    wc2 = wc*wc

    t = slt/clt
    t2 = t*t
    t4 = t2*t2
    t6 = t2*t4

    trm1 = (psi-t2)/6.0

    trm2 = (((4.0*(1.0-6.0*t2)*psi
                  + (1.0+8.0*t2))*psi
                  - 2.0*t2)*psi+t4)/120.0

    trm3 = (61.0 - 479.0*t2 + 179.0*t4 - t6)/5040.0

    gce = (sf*eta*dlon*clt)*(((trm3*wc2+trm2)*wc2+trm1)*wc2+1.0)
    ce = gce/utom+fe

    trm1 = 1.0/2.0

    trm2 = ((4.0*psi+1)*psi-t2)/24.0

    trm3 = ((((8.0*(11.0-24.0*t2)*psi
                -28.0*(1.0-6.0*t2))*psi
                +(1.0-32.0*t2))*psi
                -2.0*t2)*psi
                +t4)/720.0

    trm4 = (1385.0-3111.0*t2+543.0*t4-t6)/40320.0

    gcn = (eta*t)*((((trm4*wc2+trm3)*wc2+trm2)*wc2+trm1)*wc2)
    cn = (gcn+m-om)*sf/utom+fn

    return (ce, cn)