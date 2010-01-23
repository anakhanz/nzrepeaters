#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import os

LAT = 0
LON = 1

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

########################################################################
class Coordinate:
    """"""

    #----------------------------------------------------------------------
    def __init__(self, lat, lon):
        """Constructor"""
        assert type(lat) == float
        assert type(lon) == float
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        self.lat = lat
        self.lon = lon
########################################################################
class License:
    """"""

    #----------------------------------------------------------------------
    def __init__(self, frequency,licensee,
                 number,name=None,callsign=''):
        """Constructor"""
        assert type(frequency) == float
        self.frequency = frequency
        self.location = licensee
        self.number = number
        self.name = name
        self.callsign = callsign

    #----------------------------------------------------------------------
    def setCallsign(self,callsign):
        """Sets theh callsign"""
        self.callsign = callsign

    #----------------------------------------------------------------------
    def calcInput(self):
        """Sets theh callsign"""
        # 6m
        if 50.0 <= self.frequency <= 54.0:
            offset = 1.0
        # 2m
        elif 145.325 <= self.frequency <= 147.0:
            offset = -0.6
        elif 147.025 <= self.frequency <= 148.0:
            offset = +0.6
        # special case fo Roorua Linear
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
            raise Exception('Error no offset calculation for %fMHz' % self.frequency)
            offset = 0
        return self.frequency + offset

    #----------------------------------------------------------------------
    def kmlBasic(self):
        """returns the kml formatted output"""
        return '<tr><td>' + self.callsign +\
               '</td><td>' +'%0.3fMHz' % self.frequency +\
               '</td><td>' +\
               '</td><td>' +self.number +\
               '</td><tr>\n'

    #----------------------------------------------------------------------
    def kmlRepeater(self):
        """returns the kml formatted output"""
        return '</td><td>' +'%0.3fMHz' % self.frequency+\
               '</td><td>' +'%0.3fMHz' % self.calcInput()+\
               '</td><td>' +\
               '</td><td>' +self.number +\
               '</td><tr>\n'




########################################################################
class Licensee:
    """"""

    #----------------------------------------------------------------------
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

########################################################################
class Site:
    """"""

    #----------------------------------------------------------------------
    def __init__(self,name,mapRef,coordinates):
        """Constructor"""
        self.name = name
        self.mapRef = mapRef
        self.coordinates = coordinates
        self.beacons = []
        self.digipeaters = []
        self.repeaters = []
        self.tvRepeaters = []

    #----------------------------------------------------------------------
    def addBeacon(self,beacon):
        """"""
        self.beacons.append(beacon)

    #----------------------------------------------------------------------
    def addDigipeater(self,digipeater):
        """"""
        self.digipeaters.append(digipeater)

    #----------------------------------------------------------------------
    def addRepeater(self,repeater):
        """"""
        self.repeaters.append(repeater)

    #----------------------------------------------------------------------
    def addTvRepeater(self,tvRepeater):
        """"""
        self.tvRepeaters.append(tvRepeater)

    #----------------------------------------------------------------------
    def kmlPlacemark(self, shBeacon=True,
                     shDigipeater=True,
                     shRepeater=True,
                     shTvRepeater=True):
        """"""
        description = '<h1>Amateur Site</h1>'
        if shBeacon and len(self.beacons) > 0:
            if len(self.beacons) == 1:
                description += '<h2>Beacon</h2>'
            else:
                description += '<h2>Beacons</h2>'
            description += '<table border=1>\n'
            description += '<tr><th>Call Sign</th><th>Frequency</th><th>Licensee</th><th>License No</th></tr>\n'
            self.beacons.sort()
            for beacon in self.beacons:
                description += beacon.kmlBasic()
            description += '</table>\n'
        if shDigipeater and len(self.digipeaters) > 0:
            if len(self.digipeaters) == 1:
                description += '<h2>Digipeater</h2>'
            else:
                description += '<h2>Digipeaters</h2>'
            description += '<table border=1>\n'
            description += '<tr><th>Call Sign</th><th>Frequency</th><th>Licensee</th><th>License No</th></tr>\n'
            self.digipeaters.sort()
            for digipeater in self.digipeaters:
                description += digipeater.kmlBasic()
            description += '</table>\n'
        if shRepeater and len(self.repeaters) > 0:
            if len(self.repeaters) == 1:
                description += '<h2>Repeater</h2>'
            else:
                description += '<h2>Repeaters</h2>'
            description += '<table border=1>\n'
            description += '<tr><th>Output Frequency</th><th>Input Frequency</th><th>Licensee</th><th>License No</th></tr>\n'
            self.repeaters.sort()
            for repeater in self.repeaters:
                description += repeater.kmlRepeater()
            description += '</table>\n'
        if shTvRepeater and len(self.tvRepeaters) > 0:
            if len(self.tvRepeaters) == 1:
                description += '<h2>TV Repeater</h2>'
            else:
                description += '<h2>TV Repeaters</h2>'
            description += '<table border=1>\n'
            description += '<tr><th>Call Sign</th><th>Frequency</th><th>Licensee</th><th>License No</th></tr>\n'
            self.tvRepeaters.sort()
            for tvRepeater in self.tvRepeaters:
                description += tvRepeater.kmlBasic()
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
        return(placemark)


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__),'data')
    locations_file = os.path.join(data_dir,'sites.csv')
    licenses_file = os.path.join(data_dir,'licenses.csv')
    skip_file = os.path.join(data_dir,'skip.csv')
    kml_file = os.path.join(os.path.dirname(__file__),'test.kml')

    coordinates = {}
    for row in csv.reader(open(locations_file)):
        if row[LOCATION] != 'Location':
            coordinates[row[2]]=Coordinate(float(row[LAT]),float(row[LON]))

    skip = []
    for row in csv.reader(open(skip_file)):
        skip.append(int(row[0]))

    licencees = {}
    sites = {}

    for row in csv.reader(open(licenses_file)):
        if row[CALLSIGN] != 'Callsign':
            if row[LICENSEE] not in licencees:
                licencees[row[LICENSEE]]=Licensee(row[LICENSEE],
                                                  row[ADDRESS_1],
                                                  row[ADDRESS_2],
                                                  row[ADDRESS_3])
            if row[LOCATION] not in coordinates:
                if row[LOCATION] != 'ALL NEW ZEALAND':
                    print 'Error coordinates for "%s" not found' % row[LOCATION]
            elif int(row[LIC_NO]) in skip:
                print 'Skipping Licensee No ' + row[LIC_NO]
            else:
                if row[LOCATION] in sites:
                    site = sites[row[LOCATION]]
                else:
                    site = Site(row[LOCATION],
                                    row[MAP_REF],
                                    coordinates[row[LOCATION]])
                    sites[row[LOCATION]] = site
                license = License(float(row[FREQUENCY]),row[LICENSEE],row[LIC_NO],row[CALLSIGN])
                licType = row[LIC_TYPE]
                if license.frequency in [144.575,144.65]:
                    licType = 'Digipeater'
                if licType == 'Beacon':
                    site.addBeacon(license)
                elif licType == 'Digipeater':
                    site.addDigipeater(license)
                elif licType == 'Repeater':
                    site.addRepeater(license)
                    site.kmlPlacemark()
                elif licType == 'TV Repeater':
                    site.addTvRepeater(license)
                else:
                    print 'Funny type "%s"' % row[LIC_TYPE]
    # Generate KML file
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    kml += '  <Folder>\n'
    kml += '    <name>Amateur Sites</name>\n'
    siteNames = sites.keys()
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark()
    kml += '  </Folder>\n'
    kml += '</kml>'
    f = open(kml_file,mode='w')
    f.write(kml)
    f.close()

