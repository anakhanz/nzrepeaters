#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Repeater list builder
## URL: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2011, Rob Wallace rob[at]wallace[dot]gen[dot]nz
## Builds lists of NZ repeaters from the license information avaliable from the
## RSM's smart system.
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


import csv
import logging
import optparse
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile

import topo50
__version__ = '0.2'

USAGE = """%s [options]
NZ Repeaters %s by Rob Wallace (C)2010, Licence GPLv3
http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters""" % ("%prog",__version__)

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

class Coordinate:
    '''
    Cordinate
    '''
    def __init__(self, lat, lon):
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

LICENSE_TYPES = ['',
                 'Amateur Beacon',
                 'Amateur Digipeater',
                 'Amateur Repeater',
                 'Amateur TV Repeater']

class License:
    '''
    Amateur radio license
    '''
    def __init__(self,licType,frequency,site,licensee,
                 number,name='',callsign='', ctcss=None):
        '''
        Constructor for a license - creates the license

        Arguments:
        licType   - Type of License (Repeater, Beacon etc)
        frequency - Frequency for the license
        site      - Site name
        licensee  - Name of the License
        number    - License number
        Keyword Arguments:
        name     - Name for the licence
        callsign - Callsign for the license
        ctcss    - CTCSS Tone squelch frequency
        '''
        assert type(licType) == str or type(licType) == unicode
        assert licType in LICENSE_TYPES
        assert type(frequency) == float
        assert type(site) == str or type(site) == unicode
        assert type(licensee) == str or type(licensee) == unicode
        assert type(number) == int
        assert type(name) == str or type(name) == unicode
        assert type(callsign) == str or type(callsign) == unicode or callsign == None
        assert type(ctcss) == float or ctcss == None
        self.licType = licType
        self.frequency = frequency
        self.site = site
        self.licensee = licensee
        self.number = number
        self.name = name
        self.callsign = callsign
        self.ctcss = ctcss

    def setCallsign(self,callsign):
        '''
        Sets theh callsign associated with the license.
        '''
        self.callsign = callsign

    def setCtcss(self,ctcss):
        '''
        Sets theh CTCSS tone frequency associated with the license.
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

        else:
            logging.error('Error no offset calculation for %fMHz' % self.frequency)
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

    def htmlBasicRow(self):
        '''
        Returns an HTML table row containig the license information, formatted
        as follows:
        | Name | Callsign | Frequency | Licensee | Number |
        '''
        if self.callsign is None:
            callsign = ''
        else:
            callsign = self.callsign
        return '<tr><td>'+ self.formatName() +\
               '</td><td>' + callsign +\
               '</td><td>' +'%0.3fMHz' % self.frequency +\
               '</td><td>' + self.licensee +\
               '</td><td>' +str(self.number) +\
               '</td><tr>\n'

    def htmlRepeaterRow(self):
        '''
        Returns an HTML table row containig the license information including
        input frequency for a repeater, formatted as follows:
        | Name | Output Freq | Input Freq | CTCSS | Licensee | Number |
        '''
        if self.ctcss is None:
            ctcss = 'None'
        else:
            ctcss = '%0.1fHz' % self.ctcss
        return '<tr><td>'+ self.formatName() +\
               '</td><td>' +'%0.3fMHz' % self.frequency+\
               '</td><td>' +'%0.3fMHz' % self.calcInput()+\
               '</td><td>' +'%s' % ctcss+\
               '</td><td>' + self.licensee +\
               '</td><td>' +str(self.number) +\
               '</td><tr>\n'

    def kmlPlacemark(self, site):
        '''
        Returns a kml placemark for the license.

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
        description += '<tr><td colspan=%i><b>Site Name</b></td><td>%s</td></tr>' % (colSpan, self.site)
        description += '<tr><td colspan=%i><b>Map Reference</b></td><td>%s</td></tr>' % (colSpan, site.mapRef)
        description += '<tr><td colspan=%i><b>Coordinates</b></td><td>%f %f</td></tr>' % (colSpan, site.coordinates.lat, site.coordinates.lon)
        description += '<tr><td colspan=%i><b>License Number</b></td><td>%s</td></tr>' % (colSpan, self.number)
        description += '<tr><td colspan=%i><b>Licensee</b></td><td>%s</td></tr>' % (colSpan, self.licensee)
        description += '</table>'

        placemark = '    <Placemark>\n'
        placemark += '      <name>'+ self.formatName()+'</name>\n'
        placemark += '      <description><![CDATA['
        placemark += description
        placemark += ']]></description>\n'
        placemark += '      <Point>\n'
        placemark += '        <coordinates>'
        placemark += '%f,%f,0' % (site.coordinates.lon,site.coordinates.lat)
        placemark += '</coordinates>\n'
        placemark += '      </Point>\n'
        placemark += '    </Placemark>\n'
        return placemark


class Licensee:
    '''
    Licensee for a amateur radio licenses
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


class Site:
    '''
    Amateur radio site containing the licenses associated with it.
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
        Adds the given beacon license to the site
        '''
        assert type(beacon) == type(License('',1.1,'','',1))
        self.beacons.append(beacon)

    def addDigipeater(self,digipeater):
        '''
        Adds the given digipeater license to the site
        '''
        assert type(digipeater) == type(License('',1.1,'','',1))
        self.digipeaters.append(digipeater)

    def addRepeater(self,repeater):
        '''
        Adds the given repeater license to the site
        '''
        assert type(repeater) == type(License('',1.1,'','',1))
        self.repeaters.append(repeater)

    def addTvRepeater(self,tvRepeater):
        '''
        Adds the given TV repeater license to the site
        '''
        assert type(tvRepeater) == type(License('',1.1,'','',1))
        self.tvRepeaters.append(tvRepeater)

    def kmlPlacemark(self,
                     shBeacon=True,
                     shDigipeater=True,
                     shRepeater=True,
                     shTvRepeater=True):
        '''
        Returns a kml placemark for the site containing the requested
        information or an empty string if there are no licenses to display
        in the requested informaton.

        Keyword Arguments:
        shBeacon     - Show beacons in the information
        shDigipeater - Show digipeaters in the information
        shRepeater   - Show repeaters in the information
        shTvRepeater - Show TV repeaters in the information
        '''
        if (shBeacon and len(self.beacons) > 0) or\
           (shDigipeater and len(self.digipeaters) > 0) or\
           (shRepeater and len(self.repeaters) > 0) or\
           (shTvRepeater and len(self.tvRepeaters) >0):
            logging.debug('Creating placemark for: %s' % self.name)
            description = '<h1>Amateur Site</h1>'
            description += '<table border=1>'
            description += '<tr><td><b>Map Reference</b></td><td>%s</td></tr>' % self.mapRef
            description += '<tr><td><b>Coordinates</b></td><td>%f %f</td></tr>' % (self.coordinates.lat, self.coordinates.lon)
            description += '</table>'
            if shBeacon:
                description += self.htmlSimpleDescription(self.beacons,'Beacon')
            if shDigipeater:
                description += self.htmlSimpleDescription(self.digipeaters, 'Digipeater')
            if shRepeater:
                description += self.htmlRepeaterDescription(self.repeaters, 'Repeater')
            if shTvRepeater:
                description += self.htmlRepeaterDescription(self.tvRepeaters, 'TV Repeater')

            placemark = '    <Placemark>\n'
            placemark += '      <name>'+ self.name+'</name>\n'
            placemark += '      <description><![CDATA['
            placemark += description
            placemark += ']]></description>\n'
            placemark += '      <Point>\n'
            placemark += '        <coordinates>'
            placemark += '%f,%f,0' % (self.coordinates.lon,self.coordinates.lat)
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
                           '<th rowspan=2>Licensee</th>'+\
                           '<th rowspan=2>License No</th></tr>\n'+\
                           '<th>Output</th><th>Input</th>'
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
                           '<th>Frequency</th><th>Licensee</th>'+\
                           '<th>License No</th></tr>\n'
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
    Reads a set of float values associated with license numbers from the given csv
    file and returns them as a dictionary indexed by the license number.
    '''
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            ret[int(row[0])] = float(row[1])
    return ret

def readTextCsv(fileName):
    '''
    Reads a set of text values associated with license numbers from the given csv
    file and returns them as a dictionary indexed by the license number.
    '''
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            ret[int(row[0])] = row[1]
    return ret

def readLicences(fileName,callsigns,ctcss,names,skip,
                 vhf,uhf,
                 shBeacon,shDigipeater,shRepeater,shTvRepeater):
    '''
    Reads the license information fromt he gioven file and returns two
    dictionaries:

    sites     - A list of sites and their associated licenses
    licensees - A list of the named licensees and their details
    '''
    sites = {}
    licenses = {}
    licensees = {}

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
    if vhf and (not uhf):
        sql += "\n  AND s.frequency <= 148.0"
    elif (not vhf) and uhf:
        sql += "\n  AND s.frequency > 148.0"

    sql +="\nORDER BY l.licencenumber;"

    logging.info(sql)
    c.execute(sql)
    rows = c.fetchall()
    for row in rows:
        if row['name'] not in licensees:
            licensees[row['name']]=Licensee(row['name'],
                                              row['address1'],
                                              row['address2'],
                                              row['address3'])
        licenseLocation = row['locationname']
        licenseNumber = int(row['licencenumber'])
        licenseFrequency = float(row['frequency'])
        licenseCallsign = row['callsign']

        if licenseLocation == 'ALL NEW ZEALAND':
            logging.info('Skipping Licensee No: %d because it has the location "ALL NEW ZEALAND"' % licenseNumber)
        elif licenseNumber in skip.keys():
            logging.info('Skipping Licensee No: %d for reason "%s"' % (licenseNumber,skip[licenseNumber]))
        else:
            if licenseNumber in callsigns.keys():
                if licenseCallsign != callsigns[licenseNumber]:
                    logging.info('License No: %i callsign %s from the DB does not match the callsign %s from the CSV file' % (licenseNumber, row['callsign'], callsigns[licenseNumber]))
                    licenseCallsign = callsigns[licenseNumber]
            if licenseNumber in names.keys():
                licenseName = names[licenseNumber]
            else:
                licenseName = ''
                logging.info('License No: %i on frequency %0.3fMHz at location "%s" does not have an associated name' % (licenseNumber,licenseFrequency,licenseLocation))
            if licenseLocation in sites:
                site = sites[licenseLocation]
            else:
                c.execute("SELECT locationid FROM location WHERE locationname = ?", (licenseLocation,))
                locationId = c.fetchone()[0]
                c.execute("SELECT easting, northing FROM geographicreference WHERE locationid = ? AND georeferencetype = 'LAT/LONG (NZGD1949)'", (locationId,))
                coord = c.fetchone()
                c.execute("SELECT easting, northing FROM geographicreference WHERE locationid = ? AND georeferencetype = 'NZTM2000'", (locationId,))
                mapRef = c.fetchone()
                site = Site(licenseLocation,
                                nztmToTopo50(mapRef['easting'],mapRef['northing']),
                                Coordinate(coord['northing'],coord['easting']))
                sites[licenseLocation] = site
            licType = row['licencetype']
            if licenseFrequency in [144.575,144.65] and licType != 'Amateur Digipeater':
                logging.error('License No: %i has the wrong licence type "%s" in the DB, it should be "Amateur Digipeater"' % (licenseNumber,licType))
                licType = 'Amateur Digipeater'
            license = License(licType,
                              licenseFrequency,
                              licenseLocation,
                              row['name'],
                              licenseNumber,
                              licenseName,
                              licenseCallsign)
            if licenseNumber in ctcss.keys():
                license.setCtcss(ctcss[licenseNumber])
            if licType == 'Amateur Beacon' and shBeacon:
                site.addBeacon(license)
            elif licType == 'Amateur Digipeater' and shDigipeater:
                site.addDigipeater(license)
            elif licType == 'Amateur Repeater' and shRepeater:
                site.addRepeater(license)
            elif licType == 'Amateur TV Repeater' and shTvRepeater:
                site.addTvRepeater(license)
            licenses[licenseName] = (license)
    return sites, licenses, licensees

def generateKmlSite(fileName,
                sites,
                shBeacon=True,
                shDigipeater=True,
                shRepeater=True,
                shTvRepeater=True):
    kml = kmlHeader()
    kml += '    <name>Amateur Sites</name>\n'
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark(shBeacon=shBeacon,
                                        shDigipeater=shDigipeater,
                                        shRepeater=shRepeater,
                                        shTvRepeater=shTvRepeater)
    kml += kmlFooter()
    f = open(fileName,mode='w')
    f.write(kml)
    f.close()

def generateKmlLicense(fileName,
                       licenses,
                       sites,
                       shBeacon=True,
                       shDigipeater=True,
                       shRepeater=True,
                       shTvRepeater=True):

    licenseNames = licenses.keys()
    licenseNames.sort()
    kmlByType={}
    for t in LICENSE_TYPES:
        kmlByType[t]=''
    for license in licenseNames:
        kmlByType[licenses[license].licType] += licenses[license].kmlPlacemark(sites[licenses[license].site])
    kml = kmlHeader()
    kml += '    <name>Amateur Licenses</name>\n'
    for t in LICENSE_TYPES:
        if kmlByType[t] != "":
            kml += '    <Folder><name>%ss\n</name>' % t
            kml += kmlByType[t]
            kml += '    </Folder>\n'
    kml += kmlFooter()
    f = open(fileName,mode='w')
    f.write(kml)
    f.close()

def kmlHeader():
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    header += '  <Folder>\n'
    return header

def kmlFooter():
    footer = '  </Folder>\n'
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
                      default='xxxnonexxx',
                      help='Output to kml file kmz output will overide kml output')

    parser.add_option('-z','--kmz',
                      action='store',
                      type='string',
                      dest='kmzfilename',
                      default='xxxnonexxx',
                      help='Output to kmz file overides kml output specification')

    parser.add_option('-s','--site',
                      action='store_true',
                      dest='site',
                      default=False,
                      help='Output information by site')

    parser.add_option('-l','--license',
                      action='store_true',
                      dest='license',
                      default=False,
                      help='Output information by license')

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
    parser.add_option('-V','--VHF',
                      action='store_true',
                      dest='vhf',
                      default=False,
                      help='Include VHF repeaters/digipetears/beacons in the output (if neither VHF or UHF are specified both will be included)')
    parser.add_option('-U','--UHF',
                      action='store_true',
                      dest='uhf',
                      default=False,
                      help='Include UHF repeaters/digipetears/beacons in the output (if neither VHF or UHF are specified both will be included)')

    (options, args) = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    elif options.quiet:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.WARNING)

    if options.kmlfilename == 'xxxnonexxx' and options.kmzfilename == 'xxxnonexxx':
        parser.error('The either a kml or kmz filename must be defined otherwise no output will be generated')

    if options.license and options.site:
        parser.error('Only one of site or license may be specified')
    elif not (options.license or options.site):
        print 'Neither site or license defined using license'
        options.license = True

    if options.allTypes:
        options.beacon = True
        options.digi = True
        options.repeater = True
        options.tv = True

    if not (options.beacon or options.digi or options.repeater or options.tv):
        parser.error('Atleast one of the -b ,-d, -r or -t options must be specified for output to be generated')

    # If neither UHF or VHF are selecdted, select both
    if not(options.vhf or options.uhf):
        options.vhf = True
        options.uhf = True

    data_dir = os.path.join(module_path(),'data')
    callsigns_file = os.path.join(data_dir,'callsigns.csv')
    ctcss_file = os.path.join(data_dir,'ctcss.csv')
    locations_file = os.path.join(data_dir,'sites.csv')
    licenses_file = os.path.join(data_dir,'prism.sqlite')
    names_file = os.path.join(data_dir,'names.csv')
    skip_file = os.path.join(data_dir,'skip.csv')

    callsigns = readTextCsv(callsigns_file)
    ctcss = readFloatCsv(ctcss_file)
    names = readTextCsv(names_file)
    skip = readTextCsv(skip_file)
    sites, licenses, licensees = readLicences(licenses_file,callsigns,ctcss,
                                              names,skip,
                                              options.vhf,options.uhf,
                                              options.beacon,options.digi,
                                              options.repeater,options.tv)
    if options.kmzfilename != 'xxxnonexxx':
        logging.debug('exporting kmlfile %s' % options.kmlfilename)
        tempDir = tempfile.mkdtemp()
        options.kmlfilename = os.path.join(tempDir,'doc.kml')

    if options.kmlfilename != 'xxxnonexxx':
        if options.site:
            logging.debug('exporting kmlfile %s by site' % options.kmlfilename)
            generateKmlSite(options.kmlfilename,
                            sites,
                            options.beacon,
                            options.digi,
                            options.repeater,
                            options.tv)
        if options.license:
            logging.debug('exporting kmlfile %s by site' % options.kmlfilename)
            generateKmlLicense(options.kmlfilename,
                               licenses,
                               sites,
                               options.beacon,
                               options.digi,
                               options.repeater,
                               options.tv)

    if options.kmzfilename != 'xxxnonexxx':
        archive = zipfile.ZipFile(options.kmzfilename,
                                  mode='w',
                                  compression=zipfile.ZIP_DEFLATED)
        archive.write(options.kmlfilename, os.path.basename(options.kmlfilename).encode("utf_8"))
        archive.close()
        shutil.rmtree(tempDir)
    logging.debug('Done')


if __name__ == "__main__":
    main()

