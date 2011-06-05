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


import csv
import logging
import optparse
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile

from mapping.nz_coords import nztmToTopo50

#import topo50
__version__ = '0.1.1'

LICENCE_TYPES = ['',
                 'Amateur Beacon',
                 'Amateur Digipeater',
                 'Amateur Repeater',
                 'Amateur TV Repeater']

STYLE_MAP = {'Amateur Beacon':'#msn_beacon',
                 'Amateur Digipeater':'#msn_digipeater',
                 'Amateur Repeater':'#msn_repeater',
                 'Amateur TV Repeater':'#msn_repeater'}

# Columns in info array
I_NAME = 0
I_BRANCH = 1
I_TRUSTEE1 = 2
I_TRUSTEE2 = 3
I_NOTE = 4
# Columns in skip array
S_FREQ = 0
S_NOTE = 1
# Columns in links array
L_END1 = 0
L_END2 = 1
L_NAME = 2


USAGE = """%s [options]
NZ Repeaters %s by Rob Wallace (C)2010, Licence GPLv3
http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters""" % ("%prog",__version__)

class Coordinate:
    '''
    Cordinate
    '''
    def __init__(self, lat=0.0, lon=0.0):
        '''
        Constructor for a cordinate

        Arguments:
        lat - Latitude of the cordinate (float)
        lon - Longitude of the cordinate (float)
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

class Licence:
    '''
    Amateur radio licence
    '''
    def __init__(self,licType,frequency,site,licencee,
                 number,name='',branch='',trustee1='',trustee2='',
                 note='',callsign='', ctcss=None):
        '''
        Constructor for a licence - creates the licence

        Arguments:
        licType   - Type of Licence (Repeater, Beacon etc)
        frequency - Frequency for the licence
        site      - Site name
        licencee  - Name of the Licence
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
        assert type(licencee) == str or type(licencee) == unicode
        assert type(number) == int
        assert type(name) == str or type(name) == unicode
        assert type(branch) == str or type(branch) == unicode
        assert type(trustee1) == str or type(trustee1) == unicode
        assert type(trustee2) == str or type(trustee2) == unicode
        assert type(note) == str or type(note) == unicode
        assert type(callsign) == str or type(callsign) == unicode or callsign == None
        assert type(ctcss) == float or ctcss == None
        self.licType = licType
        self.frequency = frequency
        self.site = site
        self.licencee = licencee
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
        Sets theh callsign associated with the licence.
        '''
        self.callsign = callsign

    def setCtcss(self,ctcss):
        '''
        Sets theh CTCSS tone frequency associated with the licence.
        '''
        self.ctcss = ctcss

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
        # special case fo Rotorua Linear
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
            logging.error('Error no offset calculation for No: %i %s %fMHz' % (
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
        csv += ',"%i"' % self.number
        csv += ',"%s"' % self.licType
        csv += ',"%s"' % self.callsign
        csv += ',"%f"' % self.frequency
        csv += ',"%s"' % self.branch
        csv += ',"%s"' % self.trustee1
        csv += ',"%s"' % self.trustee2
        csv += ',"%s"' % self.note
        csv += ',"%s"' % self.licencee
        if self.ctcss == None:
            csv += ','
        else:
            csv += ',"%0.1f"' % self.ctcss
        csv += ',"%s"' % self.site
        csv += ',"%s"' % site.mapRef
        csv += ',"%s"' % site.coordinates.lat
        csv += ',"%f"' % site.coordinates.lon
        csv += '\n'
        return csv


    def htmlBasicRow(self):
        '''
        Returns an HTML table row containig the licence information, formatted
        as follows:
        | Name | Callsign | Frequency | Branch | Trustees | Notes | Licencee | Number |
        '''
        if self.callsign is None:
            callsign = ''
        else:
            callsign = self.callsign
        return '<tr><td>'+ self.formatName() +\
               '</td><td>' + callsign +\
               '</td><td>' +'%0.3fMHz' % self.frequency +\
               '</td><td>' + self.branch +\
               '</td><td>' + self.htmlTrustees() +\
               '</td><td>' + self.note +\
               '</td><td>' + self.licencee +\
               '</td><td>' +str(self.number) +\
               '</td></tr>\n'

    def htmlRepeaterRow(self):
        '''
        Returns an HTML table row containig the licence information including
        input frequency for a repeater, formatted as follows:
        | Name | Output Freq | Input Freq | CTCSS | Branch | Trustees | Notes | Licencee | Number |
        '''
        if self.ctcss is None:
            ctcss = 'None'
        else:
            ctcss = '%0.1fHz' % self.ctcss
        return '<tr><td>'+ self.formatName() +\
               '</td><td>' +'%0.3fMHz' % self.frequency+\
               '</td><td>' +'%0.3fMHz' % self.calcInput()+\
               '</td><td>' +'%s' % ctcss+\
               '</td><td>' + self.branch +\
               '</td><td>' + self.htmlTrustees() +\
               '</td><td>' + self.note +\
               '</td><td>' + self.licencee +\
               '</td><td>' +str(self.number) +\
               '</td></tr>\n'

    def htmlTrustees(self):
        if self.trustee2 == '':
            return self.trustee1
        else:
            return self.trustee1 + '<br>' + self.trustee2

    def kmlPlacemark(self, site):
        '''
        Returns a kml placemark for the licence.

        Keyword Arguments:
        '''
        description = '<table border=1>'
        if self.licType in ['Amateur Repeater','Amateur TV Repeater']:
            colSpan = 2
            description += "<tr><td rowspan=2><b>Frequency</b></td><td><b>Output</b></td><td>%0.3fMHz</td></tr>" % self.frequency
            description += "<td><b>Input</b></td><td>%0.3fMHz</td></tr>" % self.calcInput()
            if self.ctcss != None:
                description += '<tr><td colspan=%i><b>CTCSS</b></td><td>%0.1fHz</td></tr>' % (colSpan, self.ctcss)
        else:
            colSpan = 1
            description += "<tr><td><b>Frequency</b><td>%0.3fMHz</td></tr>" % self.frequency
        if self.callsign != None:
            description += '<tr><td colspan=%i><b>Callsign</b></td><td>%s</td></tr>' % (colSpan, self.callsign)
        description += '<tr><td colspan=%i><b>Type</b></td><td>%s</td></tr>' % (colSpan, self.licType)
        description += '<tr><td colspan=%i><b>Branch</b></td><td>%s</td></tr>' % (colSpan, self.branch)
        description += '<tr><td colspan=%i><b>Trustees</b></td><td>%s</td></tr>' % (colSpan, self.trustees())
        description += '<tr><td colspan=%i><b>Notes</b></td><td>%s</td></tr>' % (colSpan, self.note)
        description += '<tr><td colspan=%i><b>Site Name</b></td><td>%s</td></tr>' % (colSpan, self.site)
        description += '<tr><td colspan=%i><b>Map Reference</b></td><td>%s</td></tr>' % (colSpan, site.mapRef)
        description += '<tr><td colspan=%i><b>Coordinates</b></td><td>%f %f</td></tr>' % (colSpan, site.coordinates.lat, site.coordinates.lon)
        description += '<tr><td colspan=%i><b>Licence Number</b></td><td>%s</td></tr>' % (colSpan, self.number)
        description += '<tr><td colspan=%i><b>Licencee</b></td><td>%s</td></tr>' % (colSpan, self.licencee)
        description += '</table>'

        placemark = '    <Placemark>\n'
        placemark += '      <name>'+ self.formatName()+'</name>\n'
        placemark += '      <description><![CDATA['
        placemark += description
        placemark += ']]></description>\n'
        placemark += '      <open>0</open>'
        placemark += '      <styleUrl>' + STYLE_MAP[self.licType] + '</styleUrl>\n'
        placemark += '      <Point>\n'
        placemark += '        <coordinates>'
        placemark += '%s,0' % (site.coordinates.kml())
        placemark += '</coordinates>\n'
        placemark += '      </Point>\n'
        placemark += '    </Placemark>\n'
        return placemark


class Licencee:
    '''
    Licencee for a amateur radio licences
    '''
    def __init__(self, name, address1, address2, address3):
        """Constructor"""
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

    def kmlPlacemark(self):
        '''
        Returns a kml placemark (line) for the link
        '''
        placemark = '    <Placemark>\n'
        placemark += '      <name>%s</name>\n' % self.name
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
    def __init__(self,name,mapRef,coordinates):
        '''
        Site constructor

        Arguments:
        name        - MED name of the site
        mapRef      - The Topo 50 map refference for the site
        coordinates - A cordinate object containing th ecordinates for the site
        '''
        assert type(name) == str or type(name) == unicode
        assert type(mapRef) == str or type(mapRef) == unicode
        assert type(coordinates) == type(Coordinate(1.0,1.0))

        self.name = name
        self.mapRef = mapRef
        self.coordinates = coordinates
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

    def kmlPlacemark(self):
        '''
        Returns a kml placemark for the site containing the requested
        information or an empty string if there are no licences to display
        in the requested informaton.
        '''
        if (len(self.beacons) > 0) or\
           (len(self.digipeaters) > 0) or\
           (len(self.repeaters) > 0) or\
           (len(self.tvRepeaters) >0):
            logging.debug('Creating placemark for: %s' % self.name)
            description = '<h1>Amateur Site</h1>'
            description += '<table border=1>'
            description += '<tr><td><b>Map Reference</b></td><td>%s</td></tr>' % self.mapRef
            description += '<tr><td><b>Coordinates</b></td><td>%f %f</td></tr>' % (self.coordinates.lat, self.coordinates.lon)
            description += '</table>'
            description += self.htmlSimpleDescription(self.beacons,'Beacon')
            description += self.htmlSimpleDescription(self.digipeaters, 'Digipeater')
            description += self.htmlRepeaterDescription(self.repeaters, 'Repeater')
            description += self.htmlRepeaterDescription(self.tvRepeaters, 'TV Repeater')

            placemark = '    <Placemark>\n'
            placemark += '      <name>'+ self.name+'</name>\n'
            placemark += '      <description><![CDATA['
            placemark += description
            placemark += ']]></description>\n'
            placemark += '      <styleUrl>#msn_site</styleUrl>\n'
            placemark += '      <Point>\n'
            placemark += '        <coordinates>'
            placemark += '%s,0' % (self.coordinates.kml())
            placemark += '</coordinates>\n'
            placemark += '      </Point>\n'
            placemark += '    </Placemark>\n'
        else:
            logging.debug('Skiping creating empty placemark for: %s' % self.name)
            placemark=''
        return placemark

    def htmlRepeaterDescription(self, items, text):
        if len(items) == 0:
            return ""
        else:
            description = self.htmlDescriptionTitle(items, text)
            description += '<table border=1>\n'
            description += '<tr><th rowspan=2>Name</th>'+\
                           '<th colspan=2>Frequency</th>'+\
                           '<th rowspan=2>CTCSS</th>'+\
                           '<th rowspan=2>Branch</th>'+\
                           '<th rowspan=2>Trustees</th>'+\
                           '<th rowspan=2>Notes</th>'+\
                           '<th rowspan=2>Licencee</th>'+\
                           '<th rowspan=2>Licence No</th></tr>\n'+\
                           '<tr><th>Output</th><th>Input</th></tr>'
            items.sort()
            for item in items:
                logging.debug('creating row for repeater %i' % item.number)
                description += item.htmlRepeaterRow()
            description += '</table>\n'
            return description

    def htmlSimpleDescription(self, items, text):
        if len(items) == 0:
            return ""
        else:
            description = self.htmlDescriptionTitle(items, text)
            self.htmlDescriptionTitle(items, text)
            description += '<table border=1>\n'
            description += '<tr><th>Name</th><th>Call Sign</th>'+\
                           '<th>Frequency</th><th>Branch</th>'+\
                           '<th>Trustees</th><th>Notes</th>'+\
                           '<th>Licencee</th><th>Licence No</th></tr>\n'
            items.sort()
            for item in items:
                logging.debug('creating row for beacon %i' % item.number)
                description += item.htmlBasicRow()
            description += '</table>\n'
            return description

    def htmlDescriptionTitle(self, items, text):
        if len(items) == 1:
            title = '<h2>' + text + '</h2>'
        else:
            title = '<h2>' + text + 's</h2>'
        return title

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

def readFloatCsv(fileName):
    '''
    Reads a set of float values associated with licence numbers from the given csv
    file and returns them as a dictionary indexed by the licence number.
    '''
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            ret[int(row[0])] = float(row[1])
    return ret

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
                 shBeacon,shDigipeater,shRepeater,shTvRepeater):
    '''
    Reads the licence information fromt he given database file and returns
    the dictionaries below

    Arguments:
    fileName     - Filename to use for DB
    callsigns    - A dictionary of callsigns indexed by Linense number
    ctcss        - A dictionary of ctcss tones indexed by Linense number
    info         - A dictionary of additional info indexed by Linense number
    skip         - A dictionary of callsigns licences to skip by Linense number
    fMin         - minimum frequency to include
    fMax         - maximum frequency to include
    shBeacon     - Include beacons ?
    shDigipeater - Include digis ?
    shRepeater   - Include repeaters ?
    shTvRepeater - Include TV repeaters ?

    Returns:
    sites     - A list of sites and their associated licences
    licences  - A list of licences
    licencees - A list of the named licencees and their details
    '''
    sites = {}
    licences = {}
    licencees = {}

    con = sqlite3.connect(fileName)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    sql = '''
SELECT l.licenceid, l.licencenumber, l.callsign, l.licencetype,
       c.name, c.address1, c.address2, c.address3,
       s.frequency,
       lo.locationid, lo.locationname
FROM licence l, clientname c, spectrum s, transmitconfiguration t, location lo
WHERE c.clientid = l.clientid
  AND s.licenceid = l.licenceid
  AND t.licenceid = l.licenceid
  AND t.locationid = lo.locationid
  AND l.licencenumber NOT NULL
  AND l.licencetype  LIKE "Amateur%"
'''
    if fMin != None:
        sql += "\n  AND s.frequency >= %f" % fMin
    if fMax != None:
        sql += "\n  AND s.frequency <= %f" % fMax

    sql +="\nORDER BY s.frequency, l.licencenumber;"

    logging.info(sql)
    c.execute(sql)
    rows = c.fetchall()
    for row in rows:
        if row['name'] not in licencees:
            licencees[row['name']]=Licencee(row['name'],
                                              row['address1'],
                                              row['address2'],
                                              row['address3'])
        licenceLocation = row['locationname']
        licenceNumber = int(row['licencenumber'])
        licenceFrequency = float(row['frequency'])
        licenceCallsign = row['callsign']

        skipping = False
        if licenceLocation == 'ALL NEW ZEALAND':
            logging.info('Skipping Licencee No: %d because it has the location "ALL NEW ZEALAND"' % licenceNumber)
            skipping = True
        elif licenceNumber in skip.keys():
            skipFreq = float(skip[licenceNumber][S_FREQ])
            if skipFreq == 0.0 or skipFreq == licenceFrequency:
                skipping = True
                logging.info('Skipping Licencee No: %d, frequency %0.3f for reason "%s"' % (
                             licenceNumber,
                             licenceFrequency,
                             skip[licenceNumber][S_NOTE]))
        if not skipping:
            if licenceNumber in info.keys():
                    licenceName = info[licenceNumber][I_NAME]
            else:
                skipping = True
                logging.error('Licence No: %i on frequency %0.3fMHz at location "%s" does not have an info record' % (licenceNumber,licenceFrequency,licenceLocation))

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
                                Coordinate(coord['northing'],coord['easting']))
                sites[licenceLocation] = site
            licType = row['licencetype']
            if licenceFrequency in [144.575,144.65,144.7] and licType != 'Amateur Digipeater':
                logging.error('Licence No: %i %s on frequency %0.3fMHz has the wrong licence type "%s" in the DB, it should be "Amateur Digipeater"' % (licenceNumber,licenceName,licenceFrequency,licType))
                licType = 'Amateur Digipeater'
            licence = Licence(licType,
                              licenceFrequency,
                              licenceLocation,
                              row['name'],
                              licenceNumber,
                              licenceName,
                              info[licenceNumber][I_BRANCH],
                              info[licenceNumber][I_TRUSTEE1],
                              info[licenceNumber][I_TRUSTEE2],
                              info[licenceNumber][I_NOTE],
                              licenceCallsign)
            if licenceNumber in ctcss.keys():
                licence.setCtcss(ctcss[licenceNumber])
            if licType == 'Amateur Beacon' and shBeacon:
                site.addBeacon(licence)
                licences[licenceNumber] = (licence)
            elif licType == 'Amateur Digipeater' and shDigipeater:
                site.addDigipeater(licence)
                licences[licenceNumber] = (licence)
            elif licType == 'Amateur Repeater' and shRepeater:
                site.addRepeater(licence)
                licences[licenceNumber] = (licence)
            elif licType == 'Amateur TV Repeater' and shTvRepeater:
                site.addTvRepeater(licence)
                licences[licenceNumber] = (licence)
    return sites, licences, licencees

def readLinks(fileName, licences, sites):
    '''
    Reads the licence information from the given csv file and returns
    a list of the links

    Arguments:
    fileName     - Filename to use for DB
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

    csv = '"Name","Number","Type","Callsign","Frequency","Branch","Trustees 1","Trustees 2","Notes","Licencee","CTCSS","Site Name","Map reference","Latitude","Longitude"\n'
    for licence in licenceNos:
        csv += licences[licence].csvLine(sites[licences[licence].site])
    f = open(filename,mode='w')
    f.write(csv)
    f.close()

def generateKml(filename, licences, sites, links, bySite):
    if bySite:
        logging.debug('exporting kmlfile %s by site' % filename)
        kml = generateKmlSite(sites)
    else:
        logging.debug('exporting kmlfile %s by site' % filename)
        kml = generateKmlLicence(licences, sites, links)
    f = open(filename,mode='w')
    f.write(kml)
    f.close()

def generateKmlLicence(licences,sites,links):

    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(licences.keys(), key=sortKey)

    kmlByType={}
    for t in LICENCE_TYPES:
        kmlByType[t]=''
    for licence in licenceNos:
        kmlByType[licences[licence].licType] += licences[licence].kmlPlacemark(sites[licences[licence].site])
    kml = kmlHeader()
    kml += '    <name>Amateur Licences</name>\n'
    for t in LICENCE_TYPES:
        if kmlByType[t] != "":
            kml += '    <Folder><name>%ss</name>\n' % t
            kml += kmlByType[t]
            kml += '    </Folder>\n'
    if len(links) > 0:
        kml += '    <Folder><name>Links</name>\n'
        for link in links:
            kml += link.kmlPlacemark()
        kml += '    </Folder>\n'
    kml += kmlFooter()
    return kml

def generateKmlSite(sites):
    kml = kmlHeader()
    kml += '    <name>Amateur Sites</name>\n'
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark()
    kml += kmlFooter()
    return kml

def generateKmz(filename, licences, sites, links, bySite):
    logging.debug('exporting kmlfile %s' % filename)
    tempDir = tempfile.mkdtemp()
    kmlFilename = os.path.join(tempDir,'doc.kml')
    generateKml(kmlFilename, licences, sites, bySite, links)
    archive = zipfile.ZipFile(filename,
                              mode='w',
                              compression=zipfile.ZIP_DEFLATED)
    archive.write(kmlFilename, os.path.basename(kmlFilename).encode("utf_8"))
    archive.close()
    shutil.rmtree(tempDir)

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

    (options, args) = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    elif options.quiet:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.WARNING)

    if options.kmlfilename == None and\
       options.kmzfilename == None and\
       options.csvfilename == None:
        parser.error('Atleast one output file type must be defined or no output will be generated')

    if options.licence and options.site:
        parser.error('Only one of site or licence may be specified')
    elif not (options.licence or options.site):
        print 'Neither site or licence output specified creating output by licence'
        options.licence = True

    if options.allTypes:
        options.beacon = True
        options.digi = True
        options.repeater = True
        options.tv = True

    if not (options.beacon or options.digi or options.repeater or options.tv):
        parser.error('Atleast one of the -b ,-d, -r or -t options must be specified for output to be generated.')

    if options.minFreq > options.maxFreq:
        parser.error('The maximum frequency must be greater than the minimum frequency.')

    data_dir = os.path.join(module_path(),'data')
    callsigns_file = os.path.join(data_dir,'callsigns.csv')
    ctcss_file = os.path.join(data_dir,'ctcss.csv')
    licences_file = os.path.join(data_dir,'prism.sqlite')
    info_file = os.path.join(data_dir,'info.csv')
    skip_file = os.path.join(data_dir,'skip.csv')

    callsigns = readTextCsv(callsigns_file)
    ctcss = readFloatCsv(ctcss_file)
    info = readRowCsv(info_file,6)
    skip = readRowCsv(skip_file,3)
    sites, licences, licencees = readLicences(licences_file,callsigns,ctcss,
                                              info,skip,
                                              options.minFreq,options.maxFreq,
                                              options.beacon,options.digi,
                                              options.repeater,options.tv)

    if len(licences) == 0:
        parser.error('The selected options have excluded all licences, no output will be generated!')

    if options.csvfilename != None:
        generateCsv(options.csvfilename, licences, sites)

    if options.kmlfilename != None:
        generateKml(options.kmlfilename, licences, sites, options.site)

    if options.kmzfilename != None:
        generateKmz(options.kmzfilename, licences, sites, options.site)

if __name__ == "__main__":
    main()