#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Repeater list/map builder
## URL: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2011, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## Builds lists of NZ repeaters from the licence information avaliable from the
## RSM's smart system.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public Licence as published by
## the Free Software Foundation; either version 3 of the Licence, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public Licence for more details.
##
## You should have received a copy of the GNU General Public Licence
## along with this program. If not, see <http://www.gnu.org/licences/>.


import cgi
import csv
import datetime
import time
import logging
import optparse
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib2
import zipfile

from mapping.nz_coords import nztmToTopo50

#import topo50
__version__ = '0.1.2'

T_BEACON = 'Amateur Beacon'
T_DIGI = 'Amateur Digipeater'
T_REPEATER = 'Amateur Repeater'
T_TV = 'Amateur TV Repeater'

LICENCE_TYPES = ['',
                 T_BEACON,
                 T_DIGI,
                 T_REPEATER,
                 T_TV]

STYLE_MAP = {T_BEACON:'#msn_beacon',
             T_DIGI:'#msn_digipeater',
             T_REPEATER:'#msn_repeater',
             T_TV:'#msn_repeater'}

# Columns in info array
I_NAME = 0
I_BRANCH = 1
I_TRUSTEE1 = 2
I_TRUSTEE2 = 3
I_NOTE = 4
# Columns in skip array
S_FREQ = 0
S_NOTE = 1
# Columns in links csv file
L_END1 = 0
L_END2 = 1
L_NAME = 2
# Columns on CTCSS csv file
C_LICENCE = 0
C_FREQ = 1
C_NOTE = 2


UPDATE_URL = 'http://www.wallace.gen.nz/maps/data/'

USAGE = """%s [options]
NZ Repeaters %s by Rob Wallace (C)2010, Licence GPLv3
http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters""" % ("%prog",__version__)

def calcBand(f):
    for band in bands:
        if band.fIsIn(f):
            return band.name
    logging.error('Band for %0.4f not found' % f)
    return 'Band Not Found'

class band:
    '''
    Band
    '''
    def __init__(self,name,minF,maxF):
        '''
        Constructor for band

        Arguments:
        name -
        minF -
        maxF -
        '''
        assert type(name) == str or type(name) == unicode
        assert type(minF) == float
        assert type(maxF) == float
        assert minF < maxF
        self.name = name
        self.minF = minF
        self.maxF = maxF

    def fIsIn(self,f):
        '''
        Returns if the given frequency is within the band limits
        '''
        assert type(f) == float
        return f >= self.minF and f <= self.maxF

bands = [band('1800 meters',0.13,0.19),
         band('600 meters',0.505,0.515),
         band('160 meters',1.8,1.95),
         band('80 meters',3.5,3.9),
         band('40 meters',7.0,7.3),
         band('30 meters',10.1,10.150),
         band('20 meters',14.0,14.35),
         band('17 meters',18.068,18.168),
         band('15 meters',21.0,21.450),
         band('12 meters',24.890,24.990),
         band('11 meters',26.950,27.3),
         band('10 meters',28.0,29.7),
         band('6 meters',50.0,54.0),
         band('2 meters',144.0,148.0),
         band('70 cm',430.0,440.0),
         band('32 cm',921.0,929.0),
         band('23 cm',1240.0,1300.0),
         band('12 cm',2396.0,2450.0),
         band('9 cm',3300.0,3410.0),
         band('5 cm',5650.0,5850.0),
         band('3 cm',10000.0,10500.0),
         band('1.2 cm',24000.0,24250.0),
         band('6 mm',47000.0,47200.0),
         band('4 mm',75000.0,81000.0)]


class Coordinate:
    '''
    Coordinate
    '''
    def __init__(self, lat=0.0, lon=0.0):
        '''
        Constructor for a coordinate

        Arguments:
        lat - Latitude of the coordinate (float)
        lon - Longitude of the coordinate (float)
        '''
        assert type(lat) == float
        assert type(lon) == float
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        self.lat = lat
        self.lon = lon

    def kml(self):
        '''
        Returns the coordinates in the correct format for kml files
        '''
        return '%f,%f' % (self.lon, self.lat)

class Ctcss:
    '''
    CTCSS
    '''
    def __init__(self,freq,note):
        '''
        Constructor for a CTCSS code

        Arguments:
        freq - Frequency in decimal Hz of the tone
        note - the use of the tone
        '''
        assert type(freq) == float
        assert type(note) == str or type(note) == unicode
        self.freq = freq
        self.note = note

    def html(self):
        '''
        Returns the CTCSS information formatted for HTML
        '''
        return '%0.1f Hz<br>%s' % (self.freq, self.note)

class Licence:
    '''
    Amateur radio licence
    '''
    def __init__(self,licType,frequency,site,licensee,
                 number,name='',branch='',trustee1='',trustee2='',
                 note='',callsign='', ctcss=None):
        '''
        Constructor for a licence - creates the licence

        Arguments:
        licType   - Type of Licence (Repeater, Beacon etc)
        frequency - Frequency for the licence
        site      - Site name
        licensee  - Name of the Licence
        number    - Licence number

        Keyword Arguments:
        name     - Name for the licence
        branch   - NZART Branch that owns licence
        trustee1 - Repeater trustee 1
        trustee2 - Repeater trustee 2
        note     - Note containing misc info about the repeater
        callsign - Callsign for the licence
        ctcss    - CTCSS Tone squelch frequency
        '''
        assert type(licType) == str or type(licType) == unicode
        assert licType in LICENCE_TYPES
        assert type(frequency) == float
        assert type(site) == str or type(site) == unicode
        assert type(licensee) == str or type(licensee) == unicode
        assert type(number) == int
        assert type(name) == str or type(name) == unicode
        assert type(branch) == str or type(branch) == unicode
        assert type(trustee1) == str or type(trustee1) == unicode
        assert type(trustee2) == str or type(trustee2) == unicode
        assert type(note) == str or type(note) == unicode
        assert type(callsign) == str or type(callsign) == unicode or callsign == None
        assert type(ctcss) == float or ctcss == None
        if callsign == None:
            callsign = ''
        self.licType = licType
        self.frequency = frequency
        self.site = site
        self.licensee = licensee
        self.number = number
        self.name = name
        self.branch = branch
        self.trustee1 = trustee1
        self.trustee2 = trustee2
        self.note = note
        self.callsign = callsign
        self.ctcss = ctcss

    def setCallsign(self,callsign):
        '''
        Sets the call sign associated with the licence.
        '''
        self.callsign = callsign

    def setCtcss(self,ctcss):
        '''
        Sets the CTCSS tone frequency associated with the licence.
        '''
        self.ctcss = ctcss

    def band(self):
        '''
        Return the band name
        '''
        return calcBand(self.frequency)

    def calcInput(self):
        '''
        Returns the input frequency for the repeater.
        '''
        # 6m
        if 50.0 <= self.frequency <= 54.0:
            offset = 1.0
        # 2m
        elif 145.325 <= self.frequency <= 147.0:
            offset = -0.6
        elif 147.025 <= self.frequency <= 148.0:
            offset = +0.6
        # special case for Rotorua Linear
        elif self.frequency == 144.35:
            offset = +0.6
        # 70cm
        elif 438.0 <= self.frequency <440.0:
            offset = -5.0
        elif 433.0 <= self.frequency <435.0:
            offset = 5.0
        # 23cm
        # Special case for Mt Victoria
        elif self.frequency == 1271.2:
            offset = 20.0
        elif 1240.0 <= self.frequency <1300.0:
            offset = -20.0
        # Simplex repeaters eg VoIP
        elif 'simplex' in self.note.lower():
            offset = 0.0

        else:
            logging.error('Error no offset calculation for No: %i %s %0.4fMHz' % (
                           self.number, self.name, self.frequency))
            offset = 0
        return self.frequency + offset

    def formatName (self):
        '''
        Returns the formatted name including the frequency designator
        '''
        if self.licType == 'Amateur Repeater':
            formattedName = self.name + ' %i' % ((self.frequency*1000)%10000)
            if formattedName[-1:] == '0':
                formattedName = formattedName[:-1]
            return formattedName
        else:
            return self.name

    def csvLine(self, site):
        csv = '"%s"' % self.name
        csv += ',%i' % self.number
        csv += ',"%s"' % self.licType
        if self.callsign == None:
            csv += ','
        else:
            csv += ',"%s"' % self.callsign
        csv += ',%f' % self.frequency
        if self.branch == None:
            csv += ',""'
        else:
            csv += ',"%s"' % self.branch
        if self.trustee1 == None:
            csv += ',""'
        else:
            csv += ',"%s"' % self.trustee1
        if self.trustee2 == None:
            csv += ',""'
        else:
            csv += ',"%s"' % self.trustee2
        csv += ',"%s"' % self.note
        csv += ',"%s"' % self.licensee
        if self.ctcss == None:
            csv += ',,'
        else:
            csv += ',%0.1f' % self.ctcss.freq
            csv += ',"%s"' % self.ctcss.note
        csv += ',"%s"' % self.site
        csv += ',"%s"' % site.mapRef
        csv += ',"%s"' % site.coordinates.lat
        csv += ',"%f"' % site.coordinates.lon
        csv += ',"%i"' % site.height
        csv += '\n'
        return csv


    def htmlRow(self,site=None):
        '''
        Returns an HTML table row containing the licence information including
        input frequency for a repeater, formatted as follows:
        | Name | Output Freq  | Branch | Trustees | Notes | Licensee | Number |
        
        If the license is for a repeater the following is added after Output 
        frequency:
          Input Freq | CTCSS 
        
        If a site is passed to the function the following is added before Branch
        Input frequency and CTCSS:
          Site Name | Map ref | Height
        '''
        if self.ctcss is None:
            ctcss = 'None'
        else:
            ctcss = self.ctcss.html()
        row =  '<tr><td>'+ cgi.escape(self.formatName())
        row += '</td><td>' +'%0.3f MHz' % self.frequency
        if self.licType == T_REPEATER:
            row += '</td><td>' +'%0.3f MHz' % self.calcInput()
            row += '</td><td>' +'%s' % ctcss
        if site != None:
            row += '</td><td>' + cgi.escape(site.name)
            row += '</td><td>' + site.mapRef
            row += '</td><td>' + '%i m' % site.height
        row += '</td><td>' + self.htmlBranch()
        row += '</td><td>' + self.htmlTrustees()
        row += '</td><td>' + cgi.escape(self.note)
        row += '</td><td>' + cgi.escape(self.licensee)
        row += '</td><td>' +str(self.number)
        row += '</td></tr>'
        return row

    def htmlBranch(self):
        '''
        Returns the branch no formatted as a link to the information on the
        NZART website for HTML output
        '''
        try:
            b = int(self.branch)
            if b < 50:
                url = 'http://www.nzart.org.nz/branches/branch-data/branch-list-data-01-to-49/'
            else:
                url = 'http://www.nzart.org.nz/branches/branch-data/branch-list-data-50-to-99/'
            br = '%02i' % b
            brl = br
        except:
            url = 'http://www.nzart.org.nz/branches/branch-data/branch-list-data-50-to-99/'
            br = self.branch
            brl = 'Af'
        return '<a href="%s#%s">%s</a>' % (url, brl, br)
    
    def htmlNote(self):
        '''
        Returns an html formatted note including coverage link for digipeaters 
        '''
        if self.licType == T_DIGI and self.callsign != None and self.frequency == 144.575:
            return cgi.escape(self.note) + '<a href="http://aprs.fi/#!v=heard&ym=1207&call=a%2F' + self.callsign + '&timerange=3600" target="_blank"> APRS.FI Coverage Map</a>'
        else:
            return cgi.escape(self.note)

    def htmlDescription(self, site):
        '''
        Returns a html description for the licence.

        Keyword Argument:
        site - Site information for printing with the licence
        '''
        description = '<table>'
        if self.licType in [T_REPEATER]:
            colSpan = 2
            description += '<tr><th align="left" rowspan=2><b>Frequency</th><td><b>Output</b></td><td>%0.4fMHz</td></tr>' % self.frequency
            description += "<td><b>Input</b></td><td>%0.4f MHz</td></tr>" % self.calcInput()
            if self.ctcss != None:
                description += '<tr><th align="left" colspan=%i>CTCSS</th><td>%s</td></tr>' % (colSpan, self.ctcss.html())
        else:
            colSpan = 1
            description += '<tr><th align="left">Frequency</th><td>%0.4f MHz</td></tr>' % self.frequency
        if self.callsign != None:
            description += '<tr><th align="left" colspan=%i>Callsign</th><td>%s</td></tr>' % (colSpan, self.callsign)
        description += '<tr><th align="left" colspan=%i>Type</th><td>%s</td></tr>' % (colSpan, self.licType)
        description += '<tr><th align="left" colspan=%i>Branch</th><td>%s</td></tr>' % (colSpan, self.htmlBranch())
        description += '<tr><th align="left" colspan=%i>Trustees</th><td>%s</td></tr>' % (colSpan, self.htmlTrustees())
        description += '<tr><th align="left" colspan=%i>Notes</th><td>%s</td></tr>' % (colSpan, self.htmlNote())
        description += '<tr><th align="left" colspan=%i>Site Name</th><td>%s</td></tr>' % (colSpan, cgi.escape(self.site))
        description += '<tr><th align="left" colspan=%i>Map Reference</th><td>%s</td></tr>' % (colSpan, site.mapRef)
        description += '<tr><th align="left" colspan=%i>Coordinates</th><td>%f %f</td></tr>' % (colSpan, site.coordinates.lat, site.coordinates.lon)
        description += '<tr><th align="left" colspan=%i>Height</th><td>%i m</td></tr>' % (colSpan, site.height)
        description += '<tr><th align="left" colspan=%i>Licence Number</th><td>%s</td></tr>' % (colSpan, self.number)
        description += '<tr><th align="left" colspan=%i>Licensee</th><td>%s</td></tr>' % (colSpan, cgi.escape(self.licensee))
        description += '</table>'
        return description

    def htmlTrustees(self):
        '''
        Returns the trustees formatted as HTML
        '''
        if self.trustee2 == '':
            return self.trustee1
        else:
            return self.trustee1 + '<br>' + self.trustee2

    def js(self,site, splitNs=False):
        '''
        Returns a java script placemark generation call placemark for the licence.

        Keyword Argument:
        site - Site information for printing with the licence
        '''
        if splitNs and 'National System' in self.name:
            ns = ' National System'
        else:
            ns = ''
        return "    createMarker('%s','%s%s',%f, %f, '%s', '<h2>%s - %s</h2>%s');\n" % (
            self.licType, self.band(), ns,
            site.coordinates.lat, site.coordinates.lon,
            self.formatName(),
            self.licType, cgi.escape(self.formatName()), self.htmlDescription(site))

    def kmlPlacemark(self, site):
        '''
        Returns a kml placemark for the licence.

        Keyword Argument:
        site - Site information for printing with the licence
        '''
        placemark = '    <Placemark>\n'
        placemark += '      <name>'+ cgi.escape(self.formatName())+'</name>\n'
        placemark += '      <description><![CDATA['
        placemark += self.htmlDescription(site)
        placemark += ']]></description>\n'
        placemark += '      <styleUrl>' + STYLE_MAP[self.licType] + '</styleUrl>\n'
        placemark += '      <Point>\n'
        placemark += '        <coordinates>'
        placemark += '%s,0' % (site.coordinates.kml())
        placemark += '</coordinates>\n'
        placemark += '      </Point>\n'
        placemark += '    </Placemark>\n'
        return placemark

class Licensee:
    '''
    Licensee for a amateur radio licences
    '''
    def __init__(self, name, address1, address2, address3):
        '''
        Licensee constructor

        Arguments:
        name     - Name of the licensee
        address1 - First line of the address
        address2 - Second line of the address
        address3 - Third line of the address
        '''
        assert type(name) == str or type(name) == unicode
        assert type(address1) == str or type(address1) == unicode or address1 == None
        assert type(address2) == str or type(address2) == unicode or address2 == None
        assert type(address3) == str or type(address3) == unicode or address3 == None
        self.name = name
        self.address1 = address1
        self.address2 = address2
        self.address3 = address3

class Link:
    '''
    Link between Licences
    '''
    def __init__(self, name="", end1=Coordinate(0.0,0.0), end2=Coordinate(0.0,0.0)):
        '''
        Link construtor

        Arguments:
        name - name of the link
        end1 - coordinates for the first end of the link
        end2 - coordinates for the second end of the link
        '''
        assert type(name) == str or type(name) == unicode
        assert type(end1) == type(Coordinate())
        assert type(end2) == type(Coordinate())
        self.name = name
        self.end1 = end1
        self.end2 = end2

    def js(self, splitNs=False):
        '''
        Returns a java script function call for the link
        '''
        if splitNs and 'National System' in self.name:
            ltype = 'National System'
        else:
            ltype = 'General'
        return "createLink('%s', %f, %f, %f, %f,'%s');\n" % (
            ltype,
            self.end1.lat, self.end1.lon,
            self.end2.lat, self.end2.lon,
            cgi.escape(self.name))

    def kmlPlacemark(self):
        '''
        Returns a kml placemark (line) for the link
        '''
        placemark = '    <Placemark>\n'
        placemark += '      <name>%s</name>\n' % cgi.escape(self.name)
        #placemark += '      <description>description</description>\n'
        placemark += '      <styleUrl>#repeaterLink</styleUrl>\n'
        placemark += '      <LineString>\n'
        placemark += '        <extrude>0</extrude>\n'
        placemark += '        <tessellate>1</tessellate>\n'
        placemark += '        <altitudeMode>clampToGround</altitudeMode>\n'
        placemark += '        <coordinates> %s %s</coordinates>\n' % (self.end1.kml(), self.end2.kml())
        placemark += '      </LineString>\n'
        placemark += '    </Placemark>\n'

        return placemark


class Site:
    '''
    Amateur radio site containing the licences associated with it.
    '''
    def __init__(self,name,mapRef,coordinates,height):
        '''
        Site constructor

        Arguments:
        name        - MED name of the site
        mapRef      - The Topo 50 map reference for the site
        coordinates - A coordinate object containing the coordinates for the site
        height      - Height above sea level in meters
        '''
        assert type(name) == str or type(name) == unicode
        assert type(mapRef) == str or type(mapRef) == unicode
        assert type(coordinates) == type(Coordinate(1.0,1.0))
        assert type(height) == int

        self.name = name
        self.mapRef = mapRef
        self.coordinates = coordinates
        self.height = height
        self.beacons = []
        self.digipeaters = []
        self.repeaters = []
        self.tvRepeaters = []

    def addBeacon(self,beacon):
        '''
        Adds the given beacon licence to the site
        '''
        assert type(beacon) == type(Licence('',1.1,'','',1))
        self.beacons.append(beacon)

    def addDigipeater(self,digipeater):
        '''
        Adds the given digipeater licence to the site
        '''
        assert type(digipeater) == type(Licence('',1.1,'','',1))
        self.digipeaters.append(digipeater)

    def addRepeater(self,repeater):
        '''
        Adds the given repeater licence to the site
        '''
        assert type(repeater) == type(Licence('',1.1,'','',1))
        self.repeaters.append(repeater)

    def addTvRepeater(self,tvRepeater):
        '''
        Adds the given TV repeater licence to the site
        '''
        assert type(tvRepeater) == type(Licence('',1.1,'','',1))
        self.tvRepeaters.append(tvRepeater)

    def html(self):
        ret = ''
        desc = self.htmlDescription()
        if len(desc) > 0:
            ret += '<a id="%s"> </a>' % self.name
            ret +='<h2>'+self.name+'</h2>\n'
            ret += desc
        return ret

    def htmlDescription(self):
        description = ""
        if (len(self.beacons) > 0) or\
           (len(self.digipeaters) > 0) or\
           (len(self.repeaters) > 0) or\
           (len(self.tvRepeaters) >0):
            logging.debug('Creating placemark for: %s' % cgi.escape(self.name))
            #description += '<h2>Amateur Site</h2>'
            description += '<table>'
            description += '<tr><th align="left">Map Reference</th><td>%s</td></tr>' % self.mapRef
            description += '<tr><th align="left">Coordinates</th><td>%f %f</td></tr>' % (self.coordinates.lat, self.coordinates.lon)
            description += '<tr><th align="left">Height</th><td>%i m</td></tr>' % self.height
            description += '</table>'
            description += self.htmlItemTable(self.beacons,'Beacon')
            description += self.htmlItemTable(self.digipeaters, 'Digipeater')
            description += self.htmlItemTable(self.repeaters, 'Repeater')
            description += self.htmlItemTable(self.tvRepeaters, 'TV Repeater')
        return description

    def htmlNameLink(self):
        return '<a href="#%s">%s</a><br>' % (self.name, self.name)

    def htmlItemTable(self, items, text):
        if len(items) == 0:
            return ""
        else:
            if len(items) == 1:
                description = '<h3>' + text + '</h3>'
            else:
                description = '<h3>' + text + 's</h3>'
            description += htmlTableHeader(licType = items[0].licType)
            items.sort()
            for item in items:
                logging.debug('creating row for repeater %i' % item.number)
                description += item.htmlRow()
            description += '</table>'
            return description

    def js (self):
        return "createMarker('Site','site',%f, %f, '%s', '<h2>%s</h2>%s');\n" % (
            self.coordinates.lat, self.coordinates.lon,
            self.name, self.name, self.htmlDescription())

    def kmlPlacemark(self):
        '''
        Returns a kml placemark for the site containing the requested
        information or an empty string if there are no licences to display
        in the requested information.
        '''
        desc = self.htmlDescription()
        if len(desc) > 0:
            placemark = '    <Placemark>\n'
            placemark += '      <name>'+ cgi.escape(self.name) + '</name>\n'
            placemark += '      <description><![CDATA['
            placemark += desc
            placemark += ']]></description>\n'
            placemark += '      <styleUrl>#msn_site</styleUrl>\n'
            placemark += '      <Point>\n'
            placemark += '        <coordinates>'
            placemark += '%s,0' % (self.coordinates.kml())
            placemark += '</coordinates>\n'
            placemark += '      </Point>\n'
            placemark += '    </Placemark>\n'
        else:
            logging.debug('Skipping creating empty "Placemark" for: %s' % self.name)
            placemark=''
        return placemark

def we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""

    return hasattr(sys, "frozen")

def module_path():
    """ This will get us the program's directory,
    even if we are frozen using py2exe"""

    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding( )))

    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding( )))

def readCtcss(fileName):
    '''
    Reads the CTCSS information from the given csv file and returns
    a dictionary of CTCSS information indexed by licence number

    Arguments:
    fileName     - Filename to use for CSV file

    Returns:
    links     - A dictionary of CTCSS information indexed by licence number
    '''
    ctcss = {}

    for row in csv.reader(open(fileName)):
        if len(row) >= 3:
            ctcss[int(row[C_LICENCE])]= Ctcss(float(row[C_FREQ]),row[C_NOTE])
    return ctcss

def readRowCsv(fileName,length):
    '''
    Reads a rows from the from the given csv file and returns them as a
    dictionary indexed by the licence number (first item) without the first
    item in the array.
    '''
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) == length:
            ret[int(row[0])] = row[1:]
        elif len(row) > 1:
            logging.error('Row of bad length read')
            logging.error(row)
    return ret

def readTextCsv(fileName):
    '''
    Reads a set of text values associated with licence numbers from the given csv
    file and returns them as a dictionary indexed by the licence number.
    '''
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            ret[int(row[0])] = row[1]
    return ret

def readLicences(fileName,callsigns,ctcss,info,skip,
                 fMin,fMax,
                 shBeacon,shDigipeater,shRepeater,shTvRepeater,
                 include,exclude,branch):
    '''
    Reads the licence information from the given database file and returns
    the dictionaries below

    Arguments:
    fileName     - Filename to use for DB
    callsigns    - A dictionary of call signs indexed by Licnence number
    ctcss        - A dictionary of ctcss tones indexed by Licnense number
    info         - A dictionary of additional info indexed by Linense number
    skip         - A dictionary of licences to skip by Linense number
    fMin         - minimum frequency to include
    fMax         - maximum frequency to include
    shBeacon     - Include beacons ?
    shDigipeater - Include digis ?
    shRepeater   - Include repeaters ?
    shTvRepeater - Include TV repeaters ?
    include      - Filter licences to only include those that have this in their name
    exclude      - Filter licences to exclude those that have this in their name
    branch       - Filter licences to only include those allocated to this branch

    Returns:
    sites     - A list of sites and their associated licences
    licences  - A list of licences
    licensees - A list of the named licensees and their details
    '''
    sites = {}
    licences = {}
    licensees = {}

    con = sqlite3.connect(fileName)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    sql = '''
SELECT l.licenceid, l.licencenumber, l.callsign, l.licencetype,
       c.name, c.address1, c.address2, c.address3,
       s.frequency,
       lo.locationid, lo.locationname,lo.locationheight
FROM licence l, clientname c, spectrum s, transmitconfiguration t, location lo
WHERE c.clientid = l.clientid
  AND s.licenceid = l.licenceid
  AND t.licenceid = l.licenceid
  AND t.locationid = lo.locationid
  AND l.licencenumber NOT NULL
  AND l.licencetype  LIKE "Amateur%"'''
    if fMin != None:
        sql += "\n  AND s.frequency >= %f" % fMin
    if fMax != None:
        sql += "\n  AND s.frequency <= %f" % fMax

    sql +="\nORDER BY s.frequency, l.licencenumber;"

    logging.info(sql)
    c.execute(sql)
    rows = c.fetchall()
    for row in rows:
        if row['name'] not in licensees:
            licensees[row['name']]=Licensee(row['name'],
                                              row['address1'],
                                              row['address2'],
                                              row['address3'])
        licenceLocation = row['locationname']
        licenceNumber = int(row['licencenumber'])
        licenceFrequency = float(row['frequency'])
        licenceCallsign = row['callsign']

        skipping = False
        if licenceLocation == 'ALL NEW ZEALAND':
            logging.info('Skipping Licensee No: %d because it has the location "ALL NEW ZEALAND"' % licenceNumber)
            skipping = True
        elif licenceNumber in skip.keys():
            skipFreq = float(skip[licenceNumber][S_FREQ])
            if skipFreq == 0.0 or skipFreq == licenceFrequency:
                skipping = True
                logging.info('Skipping Licensee No: %d, frequency %0.4f at location %s for reason "%s"' % (licenceNumber, licenceFrequency, licenceLocation, skip[licenceNumber][S_NOTE]))

        if not skipping:
            if licenceNumber in info.keys():
                    licenceName = info[licenceNumber][I_NAME]
                    licenceBranch = info[licenceNumber][I_BRANCH]
                    licenceTrustee1 = info[licenceNumber][I_TRUSTEE1]
                    licenceTrustee2 = info[licenceNumber][I_TRUSTEE2]
                    licenceNote = info[licenceNumber][I_NOTE]
            else:
                logging.error('Licence No: %i on frequency %0.4fMHz at location "%s" does not have an info record' % (licenceNumber,licenceFrequency,licenceLocation))
                licenceName = licenceLocation.title()
                licenceBranch = ''
                licenceTrustee1 = ''
                licenceTrustee2 = ''
                licenceNote = ''
        
        if include != None:
            skipping = skipping or (include not in licenceName)
        if exclude != None:
            skipping = skipping or (exclude in licenceName)

        if branch != None:
            skipping = skipping or (branch != info[licenceNumber][I_BRANCH])

        if not skipping:
            if licenceNumber in callsigns.keys():
                if licenceCallsign != callsigns[licenceNumber]:
                    logging.info('Licence No: %i callsign %s from the DB does not match the callsign %s from the CSV file' % (licenceNumber, row['callsign'], callsigns[licenceNumber]))
                    licenceCallsign = callsigns[licenceNumber]
            if licenceLocation in sites:
                site = sites[licenceLocation]
            else:
                c.execute("SELECT locationid FROM location WHERE locationname = ?", (licenceLocation,))
                locationId = c.fetchone()[0]
                c.execute("SELECT easting, northing FROM geographicreference WHERE locationid = ? AND georeferencetype = 'LAT/LONG (NZGD1949)'", (locationId,))
                coord = c.fetchone()
                c.execute("SELECT easting, northing FROM geographicreference WHERE locationid = ? AND georeferencetype = 'NZTM2000'", (locationId,))
                mapRef = c.fetchone()
                site = Site(licenceLocation,
                            nztmToTopo50(mapRef['easting'],mapRef['northing']),
                            Coordinate(coord['northing'],coord['easting']),
                            row['locationheight'])
                sites[licenceLocation] = site
            licType = row['licencetype']
            if licenceFrequency in [144.575,144.65,144.7] and licType != 'Amateur Digipeater':
                logging.info('Licence No: %i %s on frequency %0.4fMHz has the wrong licence type "%s" in the DB, it should be "Amateur Digipeater"' % (licenceNumber,licenceName,licenceFrequency,licType))
                licType = 'Amateur Digipeater'
            licence = Licence(licType,
                              licenceFrequency,
                              licenceLocation,
                              row['name'],
                              licenceNumber,
                              licenceName,
                              licenceBranch,
                              licenceTrustee1,
                              licenceTrustee2,
                              licenceNote,
                              licenceCallsign)
            if licenceNumber in ctcss.keys():
                licence.setCtcss(ctcss[licenceNumber])
            if licType == T_BEACON and shBeacon:
                site.addBeacon(licence)
                licences['%i_%0.4f' % (licenceNumber,licenceFrequency)] = (licence)
            elif licType == T_DIGI and shDigipeater:
                site.addDigipeater(licence)
                licences[licenceNumber] = (licence)
            elif licType == T_REPEATER and shRepeater:
                site.addRepeater(licence)
                licences[licenceNumber] = (licence)
            elif licType == T_TV and shTvRepeater:
                site.addTvRepeater(licence)
                licences[licenceNumber] = (licence)
    return sites, licences, licensees

def readLinks(fileName, licences, sites):
    '''
    Reads the link information from the given csv file and returns
    a list of the links

    Arguments:
    fileName     - Filename to use for CSV file
    licences     - A dictionary of licences indexed by Linense number
    sites        - A dictionary of sites indexed by site name

    Returns:
    links     - A list of links
    '''
    links = []

    for row in csv.reader(open(fileName)):
        if len(row) >= 3:
            name = row[L_NAME]
            end1 = int(row[L_END1])
            end2 = int(row[L_END2])
            if (end1 in licences.keys()) and (end2 in licences.keys()):
                links.append(Link(name,
                                  sites[licences[end1].site].coordinates,
                                  sites[licences[end2].site].coordinates))
            else:
                logging.info('Skipping link %s end licence numbers  %i and %i as one or more licences is missing' % (
                                name, end1, end2))
    return links


def generateCsv(filename,licences,sites):

    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(licences.keys(), key=sortKey)

    csv = '"Name","Number","Type","Callsign","Frequency","Branch","Trustees 1","Trustees 2","Notes","Licensee","CTCSS Tone","CTCSS Note","Site Name","Map reference","Latitude","Longitude","Height"\n'
    for licence in licenceNos:
        csv += licences[licence].csvLine(sites[licences[licence].site])
    f = open(filename,mode='w')
    f.write(csv)
    f.close()

def generateHtml(filename, licences, sites, links, byLicence, bySite):
    if bySite:
        logging.debug('exporting htmlfile %s by site' % filename)
        html = generateHtmlSite(sites)
    elif byLicence:
        logging.debug('exporting htmfile %s by site' % filename)
        html= generateHtmlLicence(licences, sites, links)
    else:
        logging.debug('exporting htmfile %s by licence and site' % filename)
        html= generateHtmlAll(licences, sites, links)

    f = open(filename,mode='w')
    f.write(html)
    f.close()

def generateHtmlAll(licences,sites,links):
    [lHeader, lBody] = generateHtmlLicenceBody(licences,sites,links)
    [sHeader, sBody] = generateHtmlSiteBody(sites)
    return htmlHeader('Amateur Licences and Sites') +\
           lHeader + sHeader +\
           lBody +sBody +\
           htmlFooter()

def generateHtmlLicence(licences,sites,links):
    [header, body] = generateHtmlLicenceBody(licences,sites,links)
    return htmlHeader('Amateur Sites') + header + body +htmlFooter()

def generateHtmlLicenceBody(licences,sites,links):

    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(licences.keys(), key=sortKey)
    htmlByType={}
    for t in LICENCE_TYPES:
        htmlByType[t]={}
    for licence in licenceNos:
        l = licences[licence]
        t = l.licType
        b = l.band()
        if b not in htmlByType[t].keys():
            htmlByType[t][b] = ""
        if "Repeater" in t:
            htmlByType[t][b] += licences[licence].htmlRow(sites[licences[licence].site])
        else:
            htmlByType[t][b] += licences[licence].htmlRow(sites[licences[licence].site])
    header = '<h1>Amateur Licences</h1>'
    header += '<ul>'
    body = '<h1>Amateur Licences</h1>'
    for t in LICENCE_TYPES:
        if len(htmlByType[t]) > 0:
            header += '<li><a href="#%s">%ss</a></li>\n' % (t, t)
            header += '<ul>\n'
            body += '<a id="%s"></a>' % (t)
            body += '    <h2>%ss</h2>\n' % t
            for b in bands:
                if b.name in htmlByType[t].keys():
                    header += '<li><a href="#%s_%s">%s</a></li>' % (t ,b.name ,b.name)
                    body += '<a id="%s_%s"></a>' % (t ,b.name)
                    body += '<h3>%s</h3>' % b.name
                    body += htmlTableHeader(True, t)
                    body += htmlByType[t][b.name]
                    body += '</table>\n'
            header += '</ul>'
    header += '</ul>'

    return (header, body)

def generateHtmlSite(sites):
    [header, body] = generateHtmlSiteBody(sites)
    return htmlHeader('Amateur Sites') + header + body +htmlFooter()

def generateHtmlSiteBody(sites):
    header = '<h1>Amateur Sites</h1>'
    body = '<h1>Amateur Sites</h1>'
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        header += sites[site].htmlNameLink()
    for site in siteNames:
        body += '<hr/>'
        body += sites[site].html()
    return (header, body)

def generateJs(filename, licences, sites, links, byLicence, bySite):
    if bySite:
        logging.debug('exporting javascript file %s by site' % filename)
        js = generateJsSite(sites)
    elif byLicence:
        logging.debug('exporting javascript file %s by site' % filename)
        js = generateJsLicence(licences, sites, links)
    else:
        logging.debug('exporting javascript file %s by licence and site' % filename)
        js= generateJsAll(licences, sites, links)

    f = open(filename,mode='w')
    f.write(js)
    f.close()

def generateJsAll(licences, sites, links):
    [lMarkers ,lTree] = generateJsLicenceMarkersTree(licences, sites, True, False)
    js = "  function loadLayers() {\n"
    js += lMarkers
    js += generateJsSiteMarkers(sites)
    js += generateJsLinksMarkers(links,True)
    js += "  }\n\n"
    js += "  function loadTree() {\n"
    js += "    var tmpNode\n"
    js += "    var typeNode\n"
    js += "    var root = tree.getRoot();\n"
    js += lTree
    js += generateJsLinksTree(True, False)
    js += generateJsSiteTree()
    js += "  }\n\n"
    js += "  function highlightTree() {\n"
    js += "    tree.getNodeByProperty ( 'label' , 'Licences' ).highlight(true);\n"
    js += "    tree.getNodeByProperty ( 'label' , 'Links' ).highlight(true);\n"
    js += "  }\n"
    return js

def generateJsLicence(licences, sites, links):
    [markers ,tree] = generateJsLicenceMarkersTree(licences, sites, True, True)
    js = "  function loadLayers() {\n"
    js += markers
    js += "  }\n\n"
    js += "  function loadTree() {\n"
    js += "    var tmpNode\n"
    js += "    var typeNode\n"
    js += "    var root = tree.getRoot();\n"
    js += tree
    js += "  }\n\n"
    js += "  function highlightTree() {\n"
    js += "    tree.getNodeByProperty ( 'label' , 'Licences' ).highlight(true);\n"
    js += "  }\n"
    return js

def generateJsLicenceMarkersTree(licences, sites, splitNs, expand):

    arrays = ""
    markers = ""
    tree = "    var baseNode = new YAHOO.widget.TextNode('Licences', root, true);\n"
    lTypeBand = {}
    for t in LICENCE_TYPES:
        lTypeBand[t]=[]

    if expand:
        expand = 'true'
    else:
        expand = 'false'

    for licence in licences:
        l = licences[licence]
        t = l.licType
        b = l.band()
        if splitNs and 'National System' in l.name:
            b = b + ' National System'
        if b not in lTypeBand[t]:
            lTypeBand[t].append(b)
        markers += l.js(sites[l.site], True)
    for t in LICENCE_TYPES:
        if len(lTypeBand[t]) > 0:
            tree += "    typeNode = new YAHOO.widget.TextNode('%ss', baseNode, %s);\n" % (t, expand)
            for b in bands:
                if b.name in lTypeBand[t]:
                    arrays += "    markers['%ss-%s'] = new Array();\n" % (t, b.name)
                    tree += "    tmpNode = new YAHOO.widget.TextNode('%s', typeNode, false);\n" % b.name
                if b.name + ' National System' in lTypeBand[t]:
                    arrays += "    markers['%ss-%s National System'] = new Array();\n" % (t, b.name)
                    tree += "    tmpNode = new YAHOO.widget.TextNode('%s National System', typeNode, false);\n" % b.name
    return (arrays + markers, tree)

def generateJsSite(sites):
    js = "  function loadLayers() {\n"
    js += generateJsSiteMarkers(sites)
    js += "  }\n\n"
    js += "  function loadTree() {\n"
    js += "    var tmpNode\n"
    js += "    var typeNode\n"
    js += "    var root = tree.getRoot();\n"
    js += generateJsSiteTree()
    js += "  }\n\n"
    js += "  function highlightTree() {\n"
    js += "    tree.getNodeByProperty ( 'label' , 'Sites' ).highlight(true);\n"
    js += "  }\n"
    return js

def generateJsSiteMarkers(sites):
    js = "    markers['Sites'] = new Array();\n"
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        js += sites[site].js()
    return js

def generateJsSiteTree():
    return "    typeNode = new YAHOO.widget.TextNode('Sites', root, false);\n"

def generateJsLinksMarkers(links, splitNs):
    js = "    links['General'] = new Array();\n"
    if splitNs:
        js += "    links['National System'] = new Array();\n"
    for link in links:
        js += link.js(splitNs)
    return js

def generateJsLinksTree(splitNs, expand):
    if expand:
        expand = 'true'
    else:
        expand = 'false'
    js = "    typeNode = new YAHOO.widget.TextNode('Links', root, %s);\n" % expand
    if splitNs:
        js += "    tmpNode = new YAHOO.widget.TextNode('General', typeNode, false);\n"
        js += "    tmpNode = new YAHOO.widget.TextNode('National System', typeNode, false);\n"
    return js


def generateKml(filename, licences, sites, links, byLicence, bySite):
    if bySite:
        logging.debug('exporting kmlfile %s by site' % filename)
        kml = generateKmlSite(sites)
    elif byLicence:
        logging.debug('exporting kmlfile %s by licence' % filename)
        kml = generateKmlLicence(licences, sites, links,1)
    else:
        logging.debug('exporting kmlfile %s by site and licence' % filename)
        kml = generateKmlAll(licences, sites, links)

    f = open(filename,mode='w')
    f.write(kml)
    f.close()

def generateKmlAll(licences, sites, links):
    kml = kmlHeader()
    kml += '    <name>Amateur Licences and Sites</name><open>1</open>\n'
    kml += '    <Folder><name>Licences</name><open>1</open>\n'
    kml += generateKmlLicenceBody(licences,sites,links,0,True)
    kml += '    </Folder>\n'
    kml += generateKmlLinksBody(links,True)
    kml += '    <Folder><name>Sites</name><open>0</open>\n'
    kml += generateKmlSiteBody(sites)
    kml += '    </Folder>\n'
    kml += kmlFooter()
    return kml

def generateKmlLicence(licences,sites,links,expand=1,splitNs=False):

    kml = kmlHeader()
    kml += '    <name>Amateur Licences</name><open>1</open>\n'
    kml += generateKmlLicenceBody(licences,sites,links,expand,splitNs)
    kml += generateKmlLinksBody(links,splitNs)
    kml += kmlFooter()
    return kml

def generateKmlLicenceBody(licences,sites,links,expand,splitNs):

    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(licences.keys(), key=sortKey)
    kmlByType={}
    kml=""
    for t in LICENCE_TYPES:
        kmlByType[t]={}
    for licence in licenceNos:
        l = licences[licence]
        t = l.licType
        b = l.band()
        if splitNs and 'National System' in l.name:
            b = b + ' National System'
        if b not in kmlByType[t].keys():
            kmlByType[t][b] = ""
        kmlByType[t][b] += licences[licence].kmlPlacemark(sites[licences[licence].site])
    for t in LICENCE_TYPES:
        if len(kmlByType[t]) > 0:
            kml += '    <Folder><name>%ss</name><open>%i</open>\n' % (t,expand)
            for b in bands:
                if b.name in kmlByType[t].keys():
                    kml += '    <Folder><name>%s</name><open>0</open>\n' % b.name
                    kml += kmlByType[t][b.name]
                    kml += '    </Folder>\n'
                if b.name + ' National System' in kmlByType[t].keys():
                    kml += '    <Folder><name>%s</name><open>0</open>\n' % (b.name + ' National System')
                    kml += kmlByType[t][b.name + ' National System']
                    kml += '    </Folder>\n'
            kml += '    </Folder>'
    return kml

def generateKmlLinksBody(links, splitNs):
    general = ''
    ns = ''
    for link in links:
        if splitNs and 'National System' in link.name:
            ns += link.kmlPlacemark()
        else:
            general += link.kmlPlacemark()
    kml = ''
    if len(links) > 0:
        if splitNs:
            kml += '    <Folder><name>Links</name><open>1</open>\n'
            if len(general) >0:
                kml += '    <Folder><name>General</name><open>0</open>\n'
                kml += general
                kml += '    </Folder>\n'
            if len(ns) >0:
                kml += '    <Folder><name>National System</name><open>0</open>\n'
                kml += ns
                kml += '    </Folder>\n'
            kml += '    </Folder>\n'
        else:
            kml += '    <Folder><name>Links</name><open>0</open>\n'
            kml += general
            kml += '    </Folder>\n'
    return kml

def generateKmlSite(sites):
    kml = kmlHeader()
    kml += '    <name>Amateur Sites</name><open>1</open>\n'
    kml += generateKmlSiteBody(sites)
    kml += kmlFooter()
    return kml

def generateKmlSiteBody(sites):
    kml = ""
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark()
    return kml

def generateKmz(filename, licences, sites, links, byLicence, bySite):
    logging.debug('exporting kmlfile %s' % filename)
    tempDir = tempfile.mkdtemp()
    kmlFilename = os.path.join(tempDir,'doc.kml')
    generateKml(kmlFilename, licences, sites, links, byLicence ,bySite)
    archive = zipfile.ZipFile(filename,
                              mode='w',
                              compression=zipfile.ZIP_DEFLATED)
    archive.write(kmlFilename, os.path.basename(kmlFilename).encode("utf_8"))
    archive.close()
    shutil.rmtree(tempDir)

def htmlHeader(title):
    header = '<html><head>'
    header += '<style type="text/css">th,td{border: 2px solid #d3e7f4;}</style>'
    header += '</head><body>'
    return header

def htmlFooter():
    footer = '</body></html>'
    return footer

def htmlTableHeader(full=False, licType=T_REPEATER):
    if licType in (T_REPEATER):
        repeater =  True
        rowspan = ' rowspan=2'
    else:
        repeater = False
        rowspan = ''
    header =  '<table><tr>'
    if licType == T_BEACON:
        header += '<th' + rowspan + '>Callsign</th>'
    header += '<th' + rowspan + '>Name</th>'
    if repeater:
        header += '<th colspan=2>Frequency</th>'
        header += '<th' + rowspan + '>CTCSS</th>'
    else:
        header += '<th>Frequency</th>'
    if full:
        header += '<th' + rowspan + '>Site</th>'
        header += '<th' + rowspan + '>Map Reference</th>'
        header += '<th' + rowspan + '>Height</th>'
    header += '<th' + rowspan + '>Branch</th>'
    header += '<th' + rowspan + '>Trustees</th>'
    header += '<th' + rowspan + '>Notes</th>'
    header += '<th' + rowspan + '>Licensee</th>'
    header += '<th' + rowspan + '>Licence No</th></tr>'
    if repeater:
        header += '<tr><th>Output</th><th>Input</th></tr>'
    return header

def kmlHeader():
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    header += '<Document>\n'
    header += '''
  <StyleMap id="msn_site">
    <Pair>
      <key>normal</key>
      <styleUrl>#sn_site</styleUrl>
    </Pair>
    <Pair>
      <key>highlight</key>
      <styleUrl>#sh_site_highlight</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="sh_site_highlight">
    <IconStyle>
      <scale>1.2</scale>
      <Icon>
        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_square_highlight.png</href>
      </Icon>
    </IconStyle>
    <ListStyle>
    </ListStyle>
  </Style>
  <Style id="sn_site">
    <IconStyle>
      <scale>1.2</scale>
      <Icon>
        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_square.png</href>
      </Icon>
    </IconStyle>
    <ListStyle>
    </ListStyle>
  </Style>
  <StyleMap id="msn_beacon">
    <Pair>
      <key>normal</key>
      <styleUrl>#sn_beacon</styleUrl>
    </Pair>
    <Pair>
    <key>highlight</key>
      <styleUrl>#sh_beacon</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="sn_beacon">
      <IconStyle>
        <scale>1.1</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/blu-blank.png</href>
        </Icon>
        <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
    <ItemIcon>
      <href>http://maps.google.com/mapfiles/kml/paddle/blu-blank-lv.png</href>
    </ItemIcon>
  </ListStyle>
  </Style>
  <Style id="sh_beacon">
    <IconStyle>
      <scale>1.3</scale>
      <Icon>
        <href>http://maps.google.com/mapfiles/kml/paddle/blu-blank.png</href>
      </Icon>
      <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
      <ItemIcon>
        <href>http://maps.google.com/mapfiles/kml/paddle/blu-blank-lv.png</href>
      </ItemIcon>
    </ListStyle>
  </Style>
  <StyleMap id="msn_repeater">
    <Pair>
      <key>normal</key>
      <styleUrl>#sn_repeater</styleUrl>
    </Pair>
    <Pair>
    <key>highlight</key>
      <styleUrl>#sh_repeater</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="sn_repeater">
      <IconStyle>
        <scale>1.1</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/grn-blank.png</href>
        </Icon>
        <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
    <ItemIcon>
      <href>http://maps.google.com/mapfiles/kml/paddle/grn-blank-lv.png</href>
    </ItemIcon>
  </ListStyle>
  </Style>
  <Style id="sh_repeater">
    <IconStyle>
      <scale>1.3</scale>
      <Icon>
        <href>http://maps.google.com/mapfiles/kml/paddle/grn-blank.png</href>
      </Icon>
      <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
      <ItemIcon>
        <href>http://maps.google.com/mapfiles/kml/paddle/grn-blank-lv.png</href>
      </ItemIcon>
    </ListStyle>
  </Style>

  <StyleMap id="msn_digipeater">
    <Pair>
      <key>normal</key>
      <styleUrl>#sn_digipeater</styleUrl>
    </Pair>
    <Pair>
    <key>highlight</key>
      <styleUrl>#sh_digipeater</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="sn_digipeater">
      <IconStyle>
        <scale>1.1</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/pink-blank.png</href>
        </Icon>
        <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
    <ItemIcon>
      <href>http://maps.google.com/mapfiles/kml/paddle/pink-blank-lv.png</href>
    </ItemIcon>
  </ListStyle>
  </Style>
  <Style id="sh_digipeater">
    <IconStyle>
      <scale>1.3</scale>
      <Icon>
        <href>http://maps.google.com/mapfiles/kml/paddle/pink-blank.png</href>
      </Icon>
      <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
      <ItemIcon>
        <href>http://maps.google.com/mapfiles/kml/paddle/pink-blank-lv.png</href>
      </ItemIcon>
    </ListStyle>
  </Style>
  <Style id="repeaterLink">
    <LineStyle>
      <color>FF5AFD82</color>
      <width>4</width>
    </LineStyle>
  </Style>
'''
    return header

def kmlFooter():
    footer = '</Document>\n'
    footer += '</kml>'
    return footer

def main():
    parser = optparse.OptionParser(usage=USAGE, version=("NZ Repeaters "+__version__))
    parser.add_option('-v','--verbose',action='store_true',dest='verbose',
                            help="Verbose logging")
    parser.add_option('-D','--debug',action='store_true',dest='debug',
                            help='Debug level logging')
    parser.add_option('-q','--quiet',action='store_true',dest='quiet',
                            help='Only critical logging')

    parser.add_option('-H','--html',
                      action='store',
                      type='string',
                      dest='htmlfilename',
                      default=None,
                      help='Output to html file, may be in addition to other output types')

    parser.add_option('-j','--javascript',
                      action='store',
                      type='string',
                      dest='jsfilename',
                      default=None,
                      help='Output to javascript file, may be in addition to other output types')

    parser.add_option('-k','--kml',
                      action='store',
                      type='string',
                      dest='kmlfilename',
                      default=None,
                      help='Output to kml file, may be in addition to other output types')

    parser.add_option('-z','--kmz',
                      action='store',
                      type='string',
                      dest='kmzfilename',
                      default=None,
                      help='Output to kmz file, may be in addition to other output types')

    parser.add_option('-c','--csv',
                      action='store',
                      type='string',
                      dest='csvfilename',
                      default=None,
                      help='Output to csv file, may be in addition to other output types')

    parser.add_option('-s','--site',
                      action='store_true',
                      dest='site',
                      default=False,
                      help='Output information by site')

    parser.add_option('-l','--licence',
                      action='store_true',
                      dest='licence',
                      default=False,
                      help='Output information by licence')

    parser.add_option('-b','--beacon',
                      action='store_true',
                      dest='beacon',
                      default=False,
                      help='Include digipeaters in the generated file')
    parser.add_option('-d','--digi',
                      action='store_true',
                      dest='digi',
                      default=False,
                      help='Include digipeaters in the generated file')
    parser.add_option('-r','--repeater',
                      action='store_true',
                      dest='repeater',
                      default=False,
                      help='Include digipeaters in the generated file')
    parser.add_option('-t','--tv',
                      action='store_true',
                      dest='tv',
                      default=False,
                      help='Include digipeaters in the generated file')
    parser.add_option('-a','--all',
                      action='store_true',
                      dest='allTypes',
                      default=False,
                      help='Include all types in the generated file')

    parser.add_option('-f','--minfreq',
                      action='store',
                      type='float',
                      dest='minFreq',
                      default=None,
                      help='Filter out all below the specified frequency')
    parser.add_option('-F','--maxfreq',
                      action='store',
                      type='float',
                      dest='maxFreq',
                      default=None,
                      help='Filter out all above the specified frequency')

    parser.add_option('-i','--include',
                      action='store',
                      type='string',
                      dest='include',
                      default=None,
                      help='Filter licences to only include licences that contain [include] in their name')
    parser.add_option('-e','--exclude',
                      action='store',
                      type='string',
                      dest='exclude',
                      default=None,
                      help='Filter licences to exclude licences that contain [exclude] in their name')

    parser.add_option('-B','--branch',
                      action='store',
                      type='string',
                      dest='branch',
                      default=None,
                      help='Filter licences to only include those from the selected branch')

    parser.add_option('-u','--update',
                      action='store_true',
                      dest='update',
                      default=False,
                      help='Update data files from the Internet')
    parser.add_option('-A','--datafolder',
                      action='store',
                      type='string',
                      dest='datadir',
                      default='data',
                      help='Modify the data folder location from the default')

    (options, args) = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    elif options.quiet:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.WARNING)

    if os.path.isabs(options.datadir):
        data_dir = options.datadir
    else:
        data_dir = os.path.join(module_path(),options.datadir)

    if not os.path.isdir(data_dir):
        parser.error('Chosen data folder %s does not exist' % data_dir)

    dataDate_file = os.path.join(data_dir,'version')
    try:
        dataDate = datetime.datetime(*time.strptime(open(dataDate_file).read()[:10], "%d/%m/%Y")[0:5])
    except:
        if options.update:
            dataDate = datetime.datetime.min
        else:
            parser.error('Can not determine data date for the chosen data folder %s' % data_dir)

    if options.update:
        if not updateData(data_dir, dataDate):
            logging.error('Unable to update data files')
            exit()
    elif not os.path.isfile(dataDate_file):
        logging.error('Missing data date file please update')
        exit()
    else:
        if (datetime.datetime.now() - dataDate) > datetime.timedelta(weeks=4):
            print 'the data is more than 4 weeks old so it is recommended that you update'


    callsigns_file = os.path.join(data_dir,'callsigns.csv')
    ctcss_file = os.path.join(data_dir,'ctcss.csv')
    licences_file = os.path.join(data_dir,'prism.sqlite')
    links_file = os.path.join(data_dir,'links.csv')
    info_file = os.path.join(data_dir,'info.csv')
    skip_file = os.path.join(data_dir,'skip.csv')

    if options.htmlfilename == None and\
       options.jsfilename == None and\
       options.kmlfilename == None and\
       options.kmzfilename == None and\
       options.csvfilename == None and\
       not options.update:
        parser.error('Atleast one output file type must be defined or no output will be generated')

    if options.allTypes:
        options.beacon = True
        options.digi = True
        options.repeater = True
        options.tv = True

    if not (options.beacon or options.digi or options.repeater or options.tv):
        if options.update:
            exit()
        else:
            parser.error('Atleast one of the -b ,-d, -r or -t options must be specified for output to be generated.')

    if options.minFreq > options.maxFreq:
        parser.error('The maximum frequency must be greater than the minimum frequency.')

    if options.licence and options.site:
        parser.error('Only one of site or licence may be specified')
    elif not (options.licence or options.site):
        print 'Neither site or licence output specified creating output including licence and site'

    callsigns = readTextCsv(callsigns_file)
    ctcss = readCtcss(ctcss_file)
    info = readRowCsv(info_file,6)
    skip = readRowCsv(skip_file,3)
    sites, licences, licensees = readLicences(licences_file,callsigns,ctcss,
                                              info,skip,
                                              options.minFreq,options.maxFreq,
                                              options.beacon,options.digi,
                                              options.repeater,options.tv,
                                              options.include,options.exclude,
                                              options.branch)
    links = readLinks(links_file,licences,sites)


    if len(licences) == 0:
        parser.error('The selected options have excluded all licences, no output will be generated!')

    if options.csvfilename != None:
        generateCsv(options.csvfilename, licences, sites)

    if options.htmlfilename != None:
        generateHtml(options.htmlfilename, licences, sites, links, options.licence, options.site)

    if options.jsfilename != None:
        generateJs(options.jsfilename, licences, sites, links, options.licence, options.site)

    if options.kmlfilename != None:
        generateKml(options.kmlfilename, licences, sites, links, options.licence, options.site)

    if options.kmzfilename != None:
        generateKmz(options.kmzfilename, licences, sites, links, options.licence, options.site)

def updateData(dataFolder, localDate):
    f = urllib2.urlopen(UPDATE_URL + 'version')
    remoteDate = datetime.datetime(*time.strptime(f.read(10), "%d/%m/%Y")[0:5])
    if localDate >= remoteDate:
        print 'Data already up to date, continuing without downloading data'
        return (True)
    urlDownload(UPDATE_URL + 'data.zip', dataFolder)
    z = zipfile.ZipFile(os.path.join(dataFolder,'data.zip'))
    z.extractall(dataFolder)
    f = open(os.path.join(dataFolder,'version'),'w')
    f.write(remoteDate.strftime("%d/%m/%Y"))
    f.close()
    return(True)

def urlDownload(url, folder=None, fileName=None):
    if fileName == None:
        fileName = url.split('/')[-1]
    if folder != None:
        fileName = os.path.join(folder, fileName)
    u = urllib2.urlopen(url)
    f = open(fileName, 'w')
    meta = u.info()
    fileSize = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (fileName, fileSize)

    fileSizeDl = 0
    blockSz = 8192
    while True:
        dlBuffer = u.read(blockSz)
        if not dlBuffer:
            break

        fileSizeDl += blockSz
        f.write(dlBuffer)
        status = r"%10d  [%3.2f%%]" % (fileSizeDl, fileSizeDl * 100. / fileSize)
        status = status + chr(8)*(len(status)+1)
        print status,
    f.close()

if __name__ == "__main__":
    main()