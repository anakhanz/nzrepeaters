#!/usr/bin/env python
# -*- coding: UTF-8 -*-

## NZ Repeater list builder
## URLs: http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters
## Copyright (C) 2010, Rob Wallace rob[at]wallace[dot]gen[dot]nz
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

__version__ = '0.1pre'

USAGE = """%s [options]
NZ Repeaters %s by Rob Wallace (C)2010, Licence GPLv3
http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters""" % ("%prog",__version__)

# Column numbers in cordinates file
LAT = 0
LON = 1

# Column numbers in the licaenses file
CALLSIGN = 0
FREQUENCY = 1
LOCATION = 2
MAP_REF = 3
LICENSEE = 4
ADDRESS_1 = 5
ADDRESS_2 = 6
ADDRESS_3 = 8
LIC_TYPE = 9
LIC_NO = 10

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


class License:
    '''
    Amateur radio license
    '''
    def __init__(self,frequency,licensee,
                 number,name='',callsign=''):
        '''
        Constructor for a license - creates the license

        Arguments:
        frequency - Frequency for the license
        licensee  - Name of the License
        number    - License number
        Keywork Arguments:
        name     - Name for the licence
        callsign - Callsign for the license
        '''
        assert type(frequency) == float
        assert type(licensee) == str
        assert type(number) == int
        assert type(name) == str
        assert type(callsign) == str
        self.frequency = frequency
        self.licensee = licensee
        self.number = number
        self.name = name
        self.callsign = callsign

    def setCallsign(self,callsign):
        '''
        Sets theh callsign associated with the license.
        '''
        self.callsign = callsign

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
        elif 1240.0 <= self.frequency <1300.0:
            offset = 7.6

        else:
            logging.error('Error no offset calculation for %fMHz' % self.frequency)
            offset = 0
        return self.frequency + offset

    def htmlBasic(self):
        '''
        Returns an HTML table row containig the license information, formatted
        as follows:
        | Name | Callsign | Frequency | Licensee | Number |
        '''
        return '<tr><td>'+ self.name +\
               '</td><td>' + self.callsign +\
               '</td><td>' +'%0.3fMHz' % self.frequency +\
               '</td><td>' + self.licensee +\
               '</td><td>' +str(self.number) +\
               '</td><tr>\n'

    def htmlRepeater(self):
        '''
        Returns an HTML table row containig the license information including
        input frequency for a repeater, formatted as follows:
        | Name | Callsign | Output Freq | Input Freq | Licensee | Number |
        '''
        return '<tr><td>'+ self.name +\
               '</td><td>' +'%0.3fMHz' % self.frequency+\
               '</td><td>' +'%0.3fMHz' % self.calcInput()+\
               '</td><td>' + self.licensee +\
               '</td><td>' +str(self.number) +\
               '</td><tr>\n'


class Licensee:
    '''
    Licensee for a amateur radio licenses
    '''
    def __init__(self, name, address1, address2, address3):
        """Constructor"""
        assert type(name) == str
        assert type(address1) == str
        assert type(address2) == str
        assert type(address3) == str
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
        mapRef      - The NZMS260 map refference for the site
        coordinates - A cordinate object containing th ecordinates for the site
        '''
        assert type(name) == str
        assert type(mapRef) == str
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
        assert type(beacon) == type(License(1.1,'',1))
        self.beacons.append(beacon)

    def addDigipeater(self,digipeater):
        '''
        Adds the given digipeater license to the site
        '''
        assert type(digipeater) == type(License(1.1,'',1))
        self.digipeaters.append(digipeater)

    def addRepeater(self,repeater):
        '''
        Adds the given repeater license to the site
        '''
        assert type(repeater) == type(License(1.1,'',1))
        self.repeaters.append(repeater)

    def addTvRepeater(self,tvRepeater):
        '''
        Adds the given TV repeater license to the site
        '''
        assert type(tvRepeater) == type(License(1.1,'',1))
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
            description = '<h1>Amateur Site</h1>'
            if shBeacon and len(self.beacons) > 0:
                if len(self.beacons) == 1:
                    description += '<h2>Beacon</h2>'
                else:
                    description += '<h2>Beacons</h2>'
                description += '<table border=1>\n'
                description += self.htmlSimpleHeader()
                self.beacons.sort()
                for beacon in self.beacons:
                    description += beacon.htmlBasic()
                description += '</table>\n'
            if shDigipeater and len(self.digipeaters) > 0:
                if len(self.digipeaters) == 1:
                    description += '<h2>Digipeater</h2>'
                else:
                    description += '<h2>Digipeaters</h2>'
                description += '<table border=1>\n'
                description += self.htmlSimpleHeader()
                self.digipeaters.sort()
                for digipeater in self.digipeaters:
                    description += digipeater.htmlBasic()
                description += '</table>\n'
            if shRepeater and len(self.repeaters) > 0:
                if len(self.repeaters) == 1:
                    description += '<h2>Repeater</h2>'
                else:
                    description += '<h2>Repeaters</h2>'
                description += '<table border=1>\n'
                description += self.htmlRepeaterHeader()
                self.repeaters.sort()
                for repeater in self.repeaters:
                    description += repeater.htmlRepeater()
                description += '</table>\n'
            if shTvRepeater and len(self.tvRepeaters) > 0:
                if len(self.tvRepeaters) == 1:
                    description += '<h2>TV Repeater</h2>'
                else:
                    description += '<h2>TV Repeaters</h2>'
                description += '<table border=1>\n'
                description += self.htmlSimpleHeader()
                self.tvRepeaters.sort()
                for tvRepeater in self.tvRepeaters:
                    description += tvRepeater.htmlBasic()
                description += '</table>\n'

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
            placemark=''
        return placemark

    def htmlRepeaterHeader(self):
        '''
        Returns a html table header for a repeater license.
        '''
        return '<tr><th rowspan=2>Name</th>'+\
               '<th colspan=2>Frequency</th>'+\
               '<th rowspan=2>Licensee</th>'+\
               '<th rowspan=2>License No</th></tr>\n'+\
               '<th>Output</th><th>Input</th>'

    def htmlSimpleHeader(self):
        '''
        Returns a html table header for a simple license.
        '''
        return '<tr><th>Name</th><th>Call Sign</th>'+\
               '<th>Frequency</th><th>Licensee</th>'+\
               '<th>License No</th></tr>\n'

def main():
    parser = optparse.OptionParser(usage=USAGE, version=("NZ Repeaters "+__version__))
    parser.add_option('-v','--verbose',action='store_true',dest='verbose',
                            help="Verbose logging")
    parser.add_option('-d','--debug',action='store_true',dest='debug',
                            help='Debug level logging')
    parser.add_option('-q','--quiet',action='store_true',dest='quiet',
                            help='Only critical logging')

    (options, args) = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    elif options.quiet:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.WARNING)


    data_dir = os.path.join(os.path.dirname(__file__),'data')
    callsigns_file = os.path.join(data_dir,'callsigns.csv')
    locations_file = os.path.join(data_dir,'sites.csv')
    licenses_file = os.path.join(data_dir,'licenses.csv')
    names_file = os.path.join(data_dir,'names.csv')
    skip_file = os.path.join(data_dir,'skip.csv')
    kml_file = os.path.join(os.path.dirname(__file__),'nz_repeaters.kml')

    callsigns = readCallsigns(callsigns_file)
    coordinates = readCordinates(locations_file)
    names = readNames(names_file)
    skip = readSkip(skip_file)
    sites, licensees = readLicences(licenses_file,callsigns,coordinates,names,skip)

    generateKml(kml_file, sites)

def readCallsigns(fileName):
    '''
    Reads a set of callsigns associated with license numbers from the given csv
    file and returns them  as a dictionary indexed by the license number.
    '''
    callsigns = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            callsigns[int(row[0])] = row[1]
    return callsigns

def readCordinates(fileName):
    '''
    Reads cordinates and their associates site names from the given csv file
    and returns them as a dictionary indexed by the site name
    '''
    coordinates = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 3:
            if row[LOCATION] != 'Location':
                coordinates[row[2]]=Coordinate(float(row[LAT]),float(row[LON]))
    return coordinates

def readSkip(fileName):
    '''
    Reads a set of licenses to skip along with the reason from the given csv
    file and returns them as a dictionary indexed by the license number.
    '''
    skip = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            skip[int(row[0])] = row[1]
    return skip

def readNames(fileName):
    '''
    Reads a set of names associated with license numbers from the given csv
    file and returns them as a dictionary indexed by the license number.
    '''
    names = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            names[int(row[0])] = row[1]
    return names

def readLicences(fileName,callsigns,coordinates,names,skip):
    '''
    Reads the license information fromt he gioven file and returns two
    dictionaries:

    sites     - A list of sites and their associated licenses
    licensees - A list of the named licensees and their details
    '''
    sites = {}
    licensees = {}

    for row in csv.reader(open(fileName)):
        if row[CALLSIGN] != 'Callsign':
            if row[LICENSEE] not in licensees:
                licensees[row[LICENSEE]]=Licensee(row[LICENSEE],
                                                  row[ADDRESS_1],
                                                  row[ADDRESS_2],
                                                  row[ADDRESS_3])
            licenseLocation = row[LOCATION]
            licenseNumber = int(row[LIC_NO])
            licenseFrequency = float(row[FREQUENCY])
            if licenseLocation not in coordinates:
                if licenseLocation != 'ALL NEW ZEALAND':
                    logging.error('Error coordinates for "%s" not found' % licenseLocation)

            elif licenseNumber in skip.keys():
                logging.info('Skipping Licensee No: %d for reason "%s"' % (licenseNumber,skip[licenseNumber]))
            else:
                if licenseNumber in callsigns.keys():
                    licenseCallsign = callsigns[licenseNumber]
                else:
                    licenseCallsign = row[CALLSIGN]
                if licenseNumber in names.keys():
                    licenseName = names[licenseNumber]
                else:
                    licenseName = ''
                    logging.info('License No: %i on frequency %0.3fMHz at location "%s" does not have an associated name' % (licenseNumber,licenseFrequency,licenseLocation))
                if licenseLocation in sites:
                    site = sites[licenseLocation]
                else:
                    site = Site(licenseLocation,
                                    row[MAP_REF],
                                    coordinates[licenseLocation])
                    sites[row[LOCATION]] = site
                license = License(licenseFrequency,
                                  row[LICENSEE],
                                  licenseNumber,
                                  licenseName,
                                  licenseCallsign)
                licType = row[LIC_TYPE]
                if license.frequency in [144.575,144.65]:
                    licType = 'Digipeater'
                if licType == 'Beacon':
                    site.addBeacon(license)
                elif licType == 'Digipeater':
                    site.addDigipeater(license)
                elif licType == 'Repeater':
                    site.addRepeater(license)
                elif licType == 'TV Repeater':
                    site.addTvRepeater(license)
                else:
                    logging.error('Unsupported Linense type "%s"' % row[LIC_TYPE])
    return sites, licensees

def generateKml(fileName,
                sites,
                shBeacon=True,
                shDigipeater=True,
                shRepeater=True,
                shTvRepeater=True):
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    kml += '  <Folder>\n'
    kml += '    <name>Amateur Sites</name>\n'
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark(shBeacon=shBeacon,
                                        shDigipeater=shDigipeater,
                                        shRepeater=shRepeater,
                                        shTvRepeater=shTvRepeater)
    kml += '  </Folder>\n'
    kml += '</kml>'
    f = open(fileName,mode='w')
    f.write(kml)
    f.close()

if __name__ == "__main__":
    main()

