#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

## NZ Repeater list/map builder
## URL: https://github.com/anakhanz/nzrepeaters
## Copyright (C) 2024, Rob Wallace rob[at]wallace[dot]kiwi
## Builds lists of NZ repeaters from the licence information avaliable
## from the RSM's smart system.
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

# TODO Implement display of "Amatuer Fixed" stations

__version__ = '0.3.0'

import html
import csv
import datetime
import json
import time
import logging
import optparse
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.request, urllib.error, urllib.parse
import zipfile

from mapping.nz_coords import nztmToTopo50
from rsmapi.licences import getLicence, getLicenceList

#import topo50

T_BEACON = 'Amateur Beacon'
T_DIGI = 'Amateur Digipeater'
T_FIXED = 'Amateur Fixed'
T_REPEATER = 'Amateur Repeater'
T_TV = 'Amateur TV Repeater'

LICENCE_TYPES = [#'',
                 T_BEACON,
                 T_DIGI,
                 T_FIXED,
                 T_REPEATER,
                 T_TV]

RSM_LIC_TYPES = {T_BEACON:'H2',
                 T_DIGI:'H3',
                 T_FIXED:'H4',
                 T_REPEATER:'H1',
                 T_TV:'H9'}

LICENCE_SUB_TYPES = ['DMR',
                     'National System']

#KML/KMZ Styles
STYLE_NAMES = {T_BEACON:'beacon',
               T_DIGI:'digipeater',
               T_FIXED:'fixed',
               T_REPEATER:'repeater',
               T_TV:'tv_repeater'}

# Highlighted Marker Colours
LICENCE_COLOUR_HI = {T_BEACON:'55DAFF',
                     T_DIGI:'FF71FF',
                     T_FIXED:'333333',
                     T_REPEATER:'90EE90',
                     T_TV:'EEBB22'}

# Marker Colours
LICENCE_COLOUR = {T_BEACON:'5588FF',
                  T_DIGI:'EE4499',
                  T_FIXED:'000000',
                  T_REPEATER:'00FF00',
                  T_TV:'FFEE22'}

# Licence Iccon
LICENCE_ICON = 'radio-station'


# Site Marker Colours & Icon
SITE_COLOUR_HI = '333333'
SITE_COLOUR = '000000'
SITE_ICON = 'mobilephonetower'

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

COLUMN_HEADERS = "Name","Number","Type","Callsign","Frequency","Offset",\
                 "Branch", "Trustees","Notes","Licensee",\
                 "CTCSS Tone","CTCSS Note","Site Name","Map reference",\
                 "Latitude","Longitude","Height"

UPDATE_URL = 'http://www.wallace.gen.nz/maps/data/'

USAGE = """%s [options]
NZ Repeaters %s by Rob Wallace (C)2024, Licence GPLv3
http://rnr.wallace.gen.nz/redmine/projects/nzrepeaters""" % ("%prog",__version__)

def calcBand(f: float) -> str:
    """Calculate the  Amateur Radio Band that a given frequency is in

    Args:
        f (float): Frequency to calcuate band for

    Returns:
        str: Amateur Radio band name
    """
    for band in bands:
        if band.fIsIn(f):
            return band.name
    logging.error('Band for %0.4f not found' % f)
    return 'Band Not Found'

class band:
    """Band
    """
    def __init__(self, name: str, minF: float, maxF: float):
        """Constructor for band

        Args:
            name (str): Name of the band
            minF (float): Minimum frequency im MHz
            maxF (float): Maximum frequency in MHz
        """
        assert type(name) == str
        assert type(minF) == float
        assert type(maxF) == float
        assert minF <= maxF
        self.name = name
        self.minF = minF
        self.maxF = maxF

    def fIsIn(self,f: float) -> bool:
        """Returns if the given frequency is within the band limits

        Args:
            f (float): Frequency to check

        Returns:
            bool: True if the frequency is within the band limits, False otherwise
        """
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
         band('33 cm',921.0,929.0),
         band('23 cm',1240.0,1300.0),
         band('12 cm',2396.0,2450.0),
         band('9 cm',3300.0,3410.0),
         band('5 cm',5650.0,5850.0),
         band('3 cm',10000.0,10500.0),
         band('1.2 cm',24000.0,24250.0),
         band('6 mm',47000.0,47200.0),
         band('4 mm',75000.0,81000.0),
         band('Digital TV',506.0,506.0)]


class Coordinate:
    """
    Coordinate
    """
    def __init__(self, lat: float = 0.0, lon: float = 0.0) -> None:
        """Constructor for a coordinate

        Args:
            lat (float, optional): Latitude of the coordinate. Defaults to 0.0.
            lon (float, optional): Longitude of the coordinate. Defaults to 0.0.
        """
        assert type(lat) == float
        assert type(lon) == float
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        self.lat = lat
        self.lon = lon

    def kml(self) -> str:
        """Returns the coordinates in the correct format for kml files

        Returns:
            string: kml coordinates
        """
        return '%f,%f' % (self.lon, self.lat)

class Ctcss:
    """
    CTCSS
    """
    def __init__(self,freq: float,note: str) -> None:
        """Constructor for a CTCSS code

        Args:
            freq (float): Frequency in decimal Hz of the tone
            note (str): Note on the use of the tone
        """
        assert type(freq) == float
        assert type(note) == str
        self.freq = freq
        self.note = note

    def html(self) -> str:
        """Returns the CTCSS information formatted for HTML

        Returns:
            str: CTCSS information formatted for HTML
        """
        return '%0.1f Hz<br>%s' % (self.freq, self.note)

class Licence:
    '''
    Amateur radio licence
    '''
    def __init__(self,licType: str,frequency: float,site: str,licensee: str,
                 number: int,name: str='',branch: str='',trustee1: str='',trustee2: str='',
                 note: str='',callsign: str='', ctcss: float=None) -> None:
        """Constructor for a licence - creates the licence

        Args:
            licType (str): Type of Licence (Repeater, Beacon etc)
            frequency (float): Frequency for the licence
            site (str): Site name
            licensee (str): Name of the Licence
            number (int): Licence number
            name (str, optional): Name for the licence. Defaults to ''.
            branch (str, optional): NZART Branch that owns licence. Defaults to ''.
            trustee1 (str, optional): Repeater trustee 1. Defaults to ''.
            trustee2 (str, optional): Repeater trustee 2. Defaults to ''.
            note (str, optional): Note containing misc info about the repeater. Defaults to ''.
            callsign (str, optional): Callsign for the licence. Defaults to ''.
            ctcss (float, optional): CTCSS Tone squelch frequency. Defaults to None.
        """
        assert type(licType) == str
        assert licType in LICENCE_TYPES or licType == ''
        assert type(frequency) == float
        assert type(site) == str
        assert type(licensee) == str
        assert type(number) == int
        assert type(name) == str
        assert type(branch) == str
        assert type(trustee1) == str
        assert type(trustee2) == str
        assert type(note) == str
        assert type(callsign) == str or callsign == None
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
        self.licSubType = ''
        for subType in LICENCE_SUB_TYPES:
            if subType in name:
                self.licSubType = subType

    def setCallsign(self,callsign: str) -> None:
        """Sets the call sign associated with the licence.

        Args:
            callsign (str): New callsign
        """
        self.callsign = callsign

    def setCtcss(self,ctcss: float) -> None:
        """Sets the CTCSS tone frequency associated with the licence.

        Args:
            ctcss (float): New CTCSS tone frequency
        """
        self.ctcss = ctcss

    def band(self) -> str:
        """Return the band name

        Returns:
            _type_: Band name
        """
        return calcBand(self.frequency)

    def calcOffset(self) -> float:
        """Returns the input offset for the repeater.

        Returns:
            float: Offset in MHz
        """
        # 6m
        if 50.0 <= self.frequency <= 54.0:
            offset = -1.0
        # 2m
        # Standard
        elif 145.325 <= self.frequency <= 147.0:
            offset = -0.6
        elif 147.025 <= self.frequency <= 148.0:
            offset = +0.6
        # 70cm
        # Standard
        elif 438.0 <= self.frequency <440.0:
            offset = -5.0
        # Inverted
        elif 433.0 <= self.frequency <435.0:
            offset = 5.0
        #33cm
        elif 927.0 <= self.frequency <928.0:
            offset = -12.0
        # 23cm
        # Standard
        elif 1240.0 <= self.frequency <1300.0:
            offset = -20.0
        # Inverted
        elif 1270.0 <= self.frequency < 1274.0:
            offset = +20.0
        # Simplex repeaters eg VoIP
        elif 'simplex' in self.note.lower():
            offset = 0.0

        # Special cases
        # Oeo Road
        elif self.number == 213218:
            offset = -0.6
        # 12 Peckham Lane cross band
        elif self.number == 131963:
            offset = 433.8 - 144.935
        # Rotorua Linear
        elif self.number == 244752:
            offset = +0.6

        else:
            logging.error('Error no offset calculation for No: %i %s %0.4fMHz' % (
                           self.number, self.name, self.frequency))
            offset = 0
        return offset

    def calcInput(self) -> float:
        """Returns the input frequency for the repeater.

        Returns:
            float: Input frequency for the repeater
        """
        return self.frequency + self.calcOffset()

    def formatName (self) -> str:
        """Returns the formatted name including the frequency designator

        Returns:
            str: Formatted name including the frequency designator
        """
        if self.licType == 'Amateur Repeater':
            formattedName = self.name + ' %i' % ((self.frequency*1000)%10000)
            if formattedName[-1:] == '0':
                formattedName = formattedName[:-1]
            return formattedName
        else:
            return self.name

    def dataRow(self, site: 'Site') -> 'list[str]':
        """Generates list of the attributes of the licence

        Args:
            site (_type_): site related tot eh licence for site details

        Returns:
            list[str]: licence attributes
        """
        row = [self.name, self.number, self.licType]
        if self.callsign == None:
            row += ['']
        else:
            row += [self.callsign]
        row += [self.frequency]
        if self.licType =='Amateur Repeater':
            row += [self.calcOffset()]
        else:
            row += ['N/A']
        if self.branch == None:
            row += ['']
        else:
            row += [self.branch]
        if self.trustee2 == '':
            row += [self.trustee1]
        else:
            row += ['%s %s' % (self.trustee1, self.trustee2)]
        row += [self.note, self.licensee]
        if self.ctcss == None:
            row += ['','']
        else:
            row += ['%0.1f ' % self.ctcss.freq, self.ctcss.note]
        row += [self.site, site.mapRef, site.coordinates.lat, site.coordinates.lon, site.height]
        return row

    def htmlRow(self,site: 'Site'=None) -> str:
        """Returns an HTML table row containing the licence information including
        input frequency for a repeater, formatted as follows:
        | Name | Output Freq  | Branch | Trustees | Notes | Licensee | Number |

        If the license is for a repeater the following is added after Output
        frequency:
          Input Freq | CTCSS

        If the licence is for a Beacon the Callsign is added before the Name

        If a site is passed to the function the following is added before Branch
        Input frequency and CTCSS:
          Site Name | Map ref | Height

        Args:
            site (Site, optional): Site information to be added to the record. Defaults to None.

        Returns:
            str: HTML table row contining the description of the licence
        """
        if self.ctcss is None:
            ctcss = 'None'
        else:
            ctcss = self.ctcss.html()
        row: str =  '<tr>'
        row += '<td>%s</td>' % self.callsign
        row += '<td>'+ html.escape(self.formatName())
        row += '</td><td>' +'%0.4f MHz' % self.frequency
        if self.licType == T_REPEATER:
            row += '</td><td>' +'%0.4f MHz' % self.calcInput()
            row += '</td><td>' +'%s' % ctcss
        if site != None:
            row += '</td><td>' + html.escape(site.name)
            row += '</td><td>' + site.mapRef
            row += '</td><td>' + '%i m' % site.height
        row += '</td><td>' + self.htmlBranch()
        row += '</td><td>' + self.htmlTrustees()
        row += '</td><td>' + self.htmlNote()
        row += '</td><td>' + html.escape(self.licensee)
        row += '</td><td>' +str(self.number)
        row += '</td></tr>'
        return row

    def htmlBranch(self) -> str:
        """Returns the branch no formatted as HTML a link to the information on the
        NZART website for HTML output

        Returns:
            str: HTML formated link to branch page
        """
        try:
            br = '%02i' % int(self.branch)
        except:
            br = self.branch
        return '<a href="http://nzart.org.nz/contact/branches/%s">%s</a>' % (br, br)

    def htmlNote(self):
        """Returns an HTML formatted note including coverage link for digipeaters

        Returns:
            str: HTML formatted note
        """
        if self.licType == T_DIGI and self.callsign != None and self.frequency == 144.575:
            return html.escape(self.note) + '<a href="http://aprs.fi/#!v=heard&ym=1207&call=a%2F' + self.callsign + '&timerange=3600" target="_blank"> APRS.FI Coverage Map</a>'
        else:
            return html.escape(self.note)

    def htmlDescription(self, site: 'Site') -> str:
        """Returns a HTML description for the licence.

        Args:
            site (Site): Site information for printing with the licence

        Returns:
            _type_: HTML site description
        """
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
        description += '<tr><th align="left" colspan=%i>Site Name</th><td>%s</td></tr>' % (colSpan, html.escape(self.site))
        description += '<tr><th align="left" colspan=%i>Map Reference</th><td>%s</td></tr>' % (colSpan, site.mapRef)
        description += '<tr><th align="left" colspan=%i>Coordinates</th><td>%f %f</td></tr>' % (colSpan, site.coordinates.lat, site.coordinates.lon)
        description += '<tr><th align="left" colspan=%i>Height</th><td>%i m</td></tr>' % (colSpan, site.height)
        description += '<tr><th align="left" colspan=%i>Licence Number</th><td>%s</td></tr>' % (colSpan, self.number)
        description += '<tr><th align="left" colspan=%i>Licensee</th><td>%s</td></tr>' % (colSpan, html.escape(self.licensee))
        description += '</table>'
        return description

    def htmlTrustees(self):
        """Returns the trustees formatted as HTML

        Returns:
            str: HTML trustees list
        """
        if self.trustee2 == '':
            return self.trustee1
        else:
            return self.trustee1 + '<br>' + self.trustee2

    def js(self, site: 'Site', splitSubType: bool=False) -> str:
        """Returns a JavaScript placemark generation call placemark for the licence.

        Args:
            site (Site): Site information for printing with the licence
            splitSubType (bool, optional): True if licence subtypes should be split for each band. Defaults to False.

        Returns:
            str: JavaScript call for creating licence placemark
        """
        if splitSubType and self.licSubType != '':
            subType = ' ' + self.licSubType
        else:
            subType = ''
        return "    createMarker('%s','%s%s',%f, %f, '%s', '<h2>%s - %s</h2>%s');\n" % (
            self.licType, self.band(), subType,
            site.coordinates.lat, site.coordinates.lon,
            self.formatName(),
            self.licType, html.escape(self.formatName()), self.htmlDescription(site))

    def kmlPlacemark(self, site: 'Site') -> str:
        """Returns a KML placemark for the licence.

        Args:
            site (Site): Site information to display with the licence

        Returns:
            str: _description_
        """
        placemark = '    <Placemark>\n'
        placemark += '      <name>'+ html.escape(self.formatName())+'</name>\n'
        placemark += '      <description><![CDATA['
        placemark += self.htmlDescription(site)
        placemark += ']]></description>\n'
        placemark += '      <styleUrl>#msn_' + STYLE_NAMES[self.licType] + '</styleUrl>\n'
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
    def __init__(self, name: str, address: tuple) -> None:
        """Licensee constructor

        Args:
            name (str): Name of the licensee
            address (tuple): Address
        """
        assert type(name) == str
        self.name = name
        self.address = address

class Link:
    '''
    Link between Licences
    '''
    def __init__(self, name: str="",
                 end1: Coordinate=Coordinate(0.0,0.0),
                 end2: Coordinate=Coordinate(0.0,0.0)) -> None:
        """Link construtor

        Args:
            name (str, optional): name of the link. Defaults to "".
            end1 (Coordinate, optional): coordinates for the first end of the link. Defaults to Coordinate(0.0,0.0).
            end2 (Coordinate, optional): coordinates for the second end of the link. Defaults to Coordinate(0.0,0.0).
        """
        assert type(name) == str
        assert isinstance(end1, Coordinate)
        assert isinstance(end2, Coordinate)
        self.name = name
        self.end1 = end1
        self.end2 = end2
        self.subType = ''
        for subType in LICENCE_SUB_TYPES:
            if subType in name:
                self.subType  = subType

    def js(self, splitSubType: bool=False) -> str:
        """Returns a JavaScript function call for the link

        Args:
            splitSubType (bool, optional): True if licence subtypes should be split for each band. Defaults to False.

        Returns:
            str: JavaScript call for creating the ling
        """
        if splitSubType and self.subType != '':
            ltype = self.subType
        else:
            ltype = 'General'
        return "    createLink('%s', %f, %f, %f, %f,'%s');\n" % (
            ltype,
            self.end1.lat, self.end1.lon,
            self.end2.lat, self.end2.lon,
            html.escape(self.name))

    def kmlPlacemark(self) -> str:
        """Returns a KML placemark (line) for the link

        Returns:
            str: KML placemark for the link
        """
        placemark = '    <Placemark>\n'
        placemark += '      <name>%s</name>\n' % html.escape(self.name)
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
    def __init__(self, name: str ,mapRef :str ,coordinates: Coordinate,
                 height: int) -> None:
        """Site constructor

        Args:
            name (str): RSM name of the site
            mapRef (str): The Topo 50 map reference for the site
            coordinates (Coordinate): A coordinate object containing the coordinates for the site
            height (int): Height above sea level in meters
        """
        assert type(name) == str
        assert type(mapRef) == str
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

    def addBeacon(self, beacon: Licence) -> None:
        """Adds the given beacon licence to the site

        Args:
            beacon (Licence): Beacon licence to be added to the site
        """
        assert type(beacon) == type(Licence('',1.1,'','',1))
        self.beacons.append(beacon)

    def addDigipeater(self, digipeater: Licence) -> None:
        """Adds the given digipeater licence to the site

        Args:
            digipeater (Licence): Digipeater licence to be added to the site
        """
        assert type(digipeater) == type(Licence('',1.1,'','',1))
        self.digipeaters.append(digipeater)

    def addRepeater(self, repeater: Licence) -> None:
        """Adds the given repeater licence to the site

        Args:
            repeater (Licence): Repeater licence to be added to the site
        """
        assert type(repeater) == type(Licence('',1.1,'','',1))
        self.repeaters.append(repeater)

    def addTvRepeater(self, tvRepeater: Licence) -> None:
        """Adds the given TV repeater licence to the site

        Args:
            tvRepeater (Licence): TV repeater licence to be added to the site
        """
        assert type(tvRepeater) == type(Licence('',1.1,'','',1))
        self.tvRepeaters.append(tvRepeater)

    def html(self) -> str:
        """Build and return HTML description of the site with heading

        Returns:
            str: Site description with heading
        """
        ret = ''
        desc = self.htmlDescription()
        if len(desc) > 0:
            ret += '<a id="%s"> </a>' % self.name
            ret +='<h2>'+self.name+'</h2>\n'
            ret += desc
        return ret

    def htmlDescription(self) -> str:
        """Build and return HTML description of the site

        Returns:
            str: Site description
        """
        description = ""
        if (len(self.beacons) > 0) or\
           (len(self.digipeaters) > 0) or\
           (len(self.repeaters) > 0) or\
           (len(self.tvRepeaters) >0):
            logging.debug('Creating placemark for: %s' % html.escape(self.name))
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

    def htmlNameLink(self) -> str:
        """Return a HTML link to the site

        Returns:
            str: HTML link
        """
        return '<a href="#%s">%s</a><br>' % (self.name, self.name)

    def htmlItemTable(self, items, text) -> str:
        if len(items) == 0:
            return ""
        else:
            if len(items) == 1:
                description = '<h3>' + text + '</h3>'
            else:
                description = '<h3>' + text + 's</h3>'
            description += htmlTableHeader(licType = items[0].licType)
            items.sort(key=lambda items: items.frequency)
            for item in items:
                logging.debug('creating row for repeater %i' % item.number)
                description += item.htmlRow()
            description += '</table>'
            return description

    def js (self) -> str:

        return "    createMarker('Site','site',%f, %f, '%s', '<h2>%s</h2>%s');\n" % (
            self.coordinates.lat, self.coordinates.lon,
            self.name, self.name, self.htmlDescription())

    def kmlPlacemark(self) -> str:
        """Returns a kml placemark for the site containing the requested
        information or an empty string if there are no licences to display
        in the requested information.

        Returns:
            str: KML placemark
        """
        desc = self.htmlDescription()
        if len(desc) > 0:
            placemark = '    <Placemark>\n'
            placemark += '      <name>'+ html.escape(self.name) + '</name>\n'
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


def jsonDefault(o) -> dict:
    """Returns a dictionary for the given object
    This is used when serialising objects to a json file

    Args:
        o (object): _description_

    Returns:
        dict: Object serialised into a dictionary
    """
    return o.__dict__

def we_are_frozen() -> bool:
    """Returns True if we are frozen via py2exe.
    This will affect how we find out where we are located.

    Returns:
        bool: True if frozen via py2exe
    """
    return hasattr(sys, "frozen")

def module_path() -> str:
    """This will get us the program's directory,
    even if we are frozen using py2exe

    Returns:
        str: Path to the program's directory
    """
    if we_are_frozen():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)

def readCtcss(fileName: str) -> dict:
    """Reads the CTCSS information from the given csv file and returns
    a dictionary of CTCSS information indexed by licence number

    Args:
        fileName (str): Filename to use for CSV file

    Returns:
        dict: A dictionary of CTCSS information indexed by licence number
    """
    ctcss = {}

    for row in csv.reader(open(fileName)):
        if len(row) >= 3:
            ctcss[int(row[C_LICENCE])]= Ctcss(float(row[C_FREQ]),row[C_NOTE])
    return ctcss

def readRowCsv(fileName: str, length: int) -> dict:
    """Reads a rows from the from the given csv file and returns them as a
    dictionary indexed by the licence number (first item) without the first
    item in the array.

    Args:
        fileName (str): Filename to use for CSV file
        length (int): Expected number of items in each row

    Returns:
        dict: Rows read from file
    """
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) == length:
            ret[int(row[0])] = row[1:]
        elif len(row) > 1:
            logging.error('Row of bad length read' + str(row))
            logging.error(row)
    return ret

def readTextCsv(fileName: str) -> dict:
    """Reads a set of text values associated with licence numbers from the given csv
    file and returns them as a dictionary indexed by the licence number.

    Args:
        fileName (str): Filename to use for CSV file

    Returns:
        dict: Rows read from file
    """
    ret = {}
    for row in csv.reader(open(fileName)):
        if len(row) >= 2:
            ret[int(row[0])] = row[1]
    return ret

def getLicenceInfo(callsigns: dict, ctcss: dict, info: dict ,skip: dict,
                   fMin: float, fMax: float,
                   shBeacon: bool, shDigipeater: bool ,shRepeater: bool ,shTvRepeater: bool,
                   include: str, exclude: str, branch: str) -> list:
    """Gets the licence information from the RSM database API and returns
    the dictionaries below

    Args:
        callsigns (dict): A dictionary of call signs indexed by Licnence number
        ctcss (dict): A dictionary of ctcss tones indexed by Licnense number
        info (dict): A dictionary of additional info indexed by Linense number
        skip (dict): A dictionary of licences to skip by Linense number
        fMin (float): minimum frequency to include
        fMax (float): maximum frequency to include
        shBeacon (bool): Include beacons ?
        shDigipeater (bool): Include digis ?
        shRepeater (bool): Include repeaters ?
        shTvRepeater (bool): Include TV repeaters ?
        include (str): Filter licences to only include those that have this in their name
        exclude (str): Filter licences to exclude those that have this in their name
        branch (str): Filter licences to only include those allocated to this branch

    Returns:
        list: sites     - A list of sites and their associated licences
        list: licences  - A list of licences
        list: licensees - A list of the named licensees and their details
    """
    sites = {}
    licences = {}
    licensees = {}

    licenceTypes = []
    if shRepeater: licenceTypes.append('H1')
    if shBeacon: licenceTypes.append('H2')
    if shDigipeater: licenceTypes.append('H3')
    if shTvRepeater: licenceTypes.append('H9')

    records = getLicenceList(licenceType=licenceTypes, fromFrequency=fMin, toFrequency=fMax, sortBy='frequency', gridRefDefault='TOPO50_T')
    for basicInfo  in records:
        txDetail = getLicence(basicInfo['licenceID'],gridRefDefault='LAT_LONG_NZGD2000_D2000')
        #rxDetail = getLicence(txDetail['associatedLicenceOrRecord'][0]['licenceId']
        if basicInfo['licensee'] not in licensees:
            licensees[basicInfo['licensee']] = Licensee(basicInfo['licensee'], [x.strip() for x in txDetail['clientDetails']['physicalAddress'].split(',')])
        licenceLocation = basicInfo['location']
        licenceNumber = basicInfo['licenceNumber']
        licenceFrequency = txDetail['summary']['frequency']
        licenceCallsign = txDetail['baseCallsign']

        skipping = False
        if licenceLocation == 'ALL NEW ZEALAND':
            logging.info('Skipping Licensee No: %d because it has the location "ALL NEW ZEALAND"' % licenceNumber)
            skipping = True
        elif licenceNumber in list(skip.keys()):
            skipFreq = float(skip[licenceNumber][S_FREQ])
            if skipFreq == 0.0 or skipFreq == licenceFrequency:
                skipping = True
                logging.info('Skipping Licensee No: %d, frequency %0.4f at location %s for reason "%s"' % (licenceNumber, licenceFrequency, licenceLocation, skip[licenceNumber][S_NOTE]))

        licenceName = licenceLocation.title()
        licenceBranch = ''
        licenceTrustee1 = ''
        licenceTrustee2 = ''
        licenceNote = 'No info record available'
        if not skipping:
            if licenceNumber in list(info.keys()):
                    licenceName = info[licenceNumber][I_NAME]
                    licenceBranch = info[licenceNumber][I_BRANCH]
                    licenceTrustee1 = info[licenceNumber][I_TRUSTEE1]
                    licenceTrustee2 = info[licenceNumber][I_TRUSTEE2]
                    licenceNote = info[licenceNumber][I_NOTE]
            else:
                logging.error('Licence No: %i on frequency %0.4fMHz at location "%s" does not have an info record' % (licenceNumber,licenceFrequency,licenceLocation))

        if include != None:
            skipping = skipping or (include not in licenceName)
        if exclude != None:
            skipping = skipping or (exclude in licenceName)

        if branch != None:
            skipping = skipping or (branch != licenceBranch)

        if not skipping:
            if licenceNumber in list(callsigns.keys()):
                if licenceCallsign != callsigns[licenceNumber]:
                    logging.info('Licence No: %i callsign %s from the DB does not match the callsign %s from the CSV file' % (licenceNumber, licenceCallsign, callsigns[licenceNumber]))
                    licenceCallsign = callsigns[licenceNumber]
            if licenceLocation in sites:
                site = sites[licenceLocation]
            else:
                easting,northing = txDetail['summary']['gridReference'].split()
                easting = float(easting)
                northing = float(northing)
                site = Site(licenceLocation,
                            basicInfo['gridReference'],
                            Coordinate(northing,easting),
                            txDetail['transmitLocations'][0]['locationAltitude'])
                sites[licenceLocation] = site
            licType = basicInfo['licenceType']
            if licenceFrequency in [144.575,144.65,144.7] and licType != 'Amateur Digipeater':
                logging.info('Licence No: %i %s on frequency %0.4fMHz has the wrong licence type "%s" in the DB, it should be "Amateur Digipeater"' % (licenceNumber,licenceName,licenceFrequency,licType))
                licType = 'Amateur Digipeater'
            licence = Licence(licType,
                              licenceFrequency,
                              licenceLocation,
                              basicInfo['location'],
                              licenceNumber,
                              licenceName,
                              licenceBranch,
                              licenceTrustee1,
                              licenceTrustee2,
                              licenceNote,
                              licenceCallsign)
            if licenceNumber in list(ctcss.keys()):
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


def readLinks(fileName: str, licences: dict, sites: dict) -> list:
    """Reads the link information from the given csv file and returns
    a list of the link

    Args:
        fileName (str): Filename to use for CSV file
        licences (dict): A dictionary of licences indexed by Linense number
        sites (dict): A dictionary of sites indexed by site name

    Returns:
        list: A list of links
    """
    links = []

    for row in csv.reader(open(fileName)):
        if len(row) >= 3:
            name = row[L_NAME]
            end1 = int(row[L_END1])
            end2 = int(row[L_END2])
            if (end1 in list(licences.keys())) and (end2 in list(licences.keys())):
                links.append(Link(name,
                                  sites[licences[end1].site].coordinates,
                                  sites[licences[end2].site].coordinates))
            else:
                logging.info('Skipping link %s end licence numbers  %i and %i as one or more licences is missing' % (
                                name, end1, end2))
    return links

def generateCsv(filename: str,licences: Licence, sites: Site) -> None:
    """Generate a CSV file of the given licences

    Args:
        filename (str): filename to save the CSV file to
        licences (Licence): licences to generates CSV file for
        sites (Site): listes to get site information from
    """
    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(list(licences.keys()), key=sortKey)

    with open(filename, 'w',  newline='') as csvfile:
        logWriter = csv.writer(csvfile, dialect='excel')
        logWriter.writerow(COLUMN_HEADERS)
        for licence in licenceNos:
            logWriter.writerow(licences[licence].dataRow(sites[licences[licence].site]))
    return
def as_text(value: any) -> str:
    """Returns the value as a str"""
    if value is None:
        return ""
    else:
        return str(value)

def generateXlsx(filename: str,licences: Licence, sites: Site) -> None:
    """Generate a XLSX file of the given licences

    Args:
        filename (str): filename to save the XLSX file to
        licences (Licence): licences to generates XLSX file for
        sites (Site): istes to get site information from
    """
    # TODO Add number formatting for Frequency and offset
    # Check if openpyxl is missing and termintae if it is missing
    try:
        import openpyxl
        from openpyxl import Workbook
        from openpyxl.formatting.rule import Rule
        from openpyxl.styles import PatternFill
        from openpyxl.styles.differential import DifferentialStyle
        from openpyxl.worksheet.table import Table, TableStyleInfo
    except ModuleNotFoundError:
        print('The openpyxl module is not installed please try another output',
              'format or install the openpyxl package.')
        sys.exit(1)

    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(list(licences.keys()), key=sortKey)

    tableRange = 'A1:Q' + str(len(licences)+1)
    tableName = 'TABLE_LICENCES'

    wb = Workbook()
    ws = wb.active
    ws.title = "Licences"

    # Insert header
    ws.append(COLUMN_HEADERS)
    # Insert Licences
    for licence in licenceNos:
        ws.append(licences[licence].dataRow(sites[licences[licence].site]))

    # Convert licences entries into a table
    tab = Table(displayName=tableName, ref=tableRange)
    # Add a default style with striped rows and banded columns
    style = TableStyleInfo(name="TableStyleMedium9",
                           showFirstColumn=False,
                           showLastColumn=False,
                           showRowStripes=True,
                           showColumnStripes=False)
    tab.tableStyleInfo = style
    ws.add_table(tab)
    # Freeze the top row
    ws.freeze_panes = 'A2'
    # Adjust the columns to fit the text
    if float(openpyxl.__version__[0:3]) >= 2.6:
        for column_cells in ws.columns:
            length = max(len(as_text(cell.value)) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = length
    else:
        for column_cells in ws.columns:
            length = max(len(as_text(cell.value)) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column].width = length
    wb.save(filename)

def generateHtml(filename: str, licences: Licence, sites: Site, links: Link,
                 byLicence: bool, bySite: bool, dataDate: datetime) -> None:
    """Generate HTML file from the given licences and sites

    Args:
        filename (str): filename to save the generated HTML to
        licences (Licence): licences to generate HTML for
        sites (Site): sites to generate HTML for
        links (Link): links to generate HTML for
        byLicence (bool): if True only generate HTML by licence
        bySite (bool): if True only generate HTML by site
        dataDate (datyetime): Data update date
    """
    dateLine = '<p>Data updated on %s</p>\n' % dataDate.strftime("%d/%m/%Y")
    if bySite:
        logging.debug('exporting htmlfile %s by site' % filename)
        html = generateHtmlSite(sites, dateLine)
    elif byLicence:
        logging.debug('exporting htmfile %s by site' % filename)
        html= generateHtmlLicence(licences, sites, links, dateLine)
    else:
        logging.debug('exporting htmfile %s by licence and site' % filename)
        html= generateHtmlAll(licences, sites, links, dateLine)

    f = open(filename,mode='w')
    f.write(html)
    f.close()

def generateHtmlAll(licences: Licence, sites: Site, links: Link, dateLine: datetime):
    """Generate HTML file for the given licences and sites

    Args:
        filename (str): filename to save the generated HTML to
        licences (Licence): licences to generate HTML for
        sites (Site): sites to generate HTML for
        links (Link): links to generate HTML for
        dataDate (datyetime): Data update date
    """
    [lHeader, lBody] = generateHtmlLicenceBody(licences,sites,links)
    [sHeader, sBody] = generateHtmlSiteBody(sites)
    return htmlHeader() +\
           dateLine +\
           lHeader + sHeader +\
           lBody +sBody +\
           htmlFooter()

def generateHtmlLicence(licences: Licence, sites: Site, links: Link, dateLine: datetime):
    """Generate HTML file for the given licences

    Args:
        filename (str): filename to save the generated HTML to
        licences (Licence): licences to generate HTML for
        sites (Site): sites to generate HTML for
        links (Link): links to generate HTML for
        dataDate (datyetime): Data update date
    """
    [header, body] = generateHtmlLicenceBody(licences,sites,links)
    return htmlHeader() + dateLine + header + body +htmlFooter()

def generateHtmlLicenceBody(licences: Licence, sites: Site, links: Link) -> str:
    """Generate HTML licence information for inclusion in a HTML file

    Args:
        licences (Licence): licences to generate HTML for
        sites (Site): Sites to generate licenec info from
        links (Link): Links to generate licence info from

    Returns:
        str: HTML licence information
    """
    def sortKey(item):
        return (licences[item].frequency, licences[item].name)

    licenceNos = sorted(list(licences.keys()), key=sortKey)
    htmlByType={}
    for t in LICENCE_TYPES:
        htmlByType[t]={}
    for licence in licenceNos:
        l = licences[licence]
        t = l.licType
        b = l.band()
        if b not in list(htmlByType[t].keys()):
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
                if b.name in list(htmlByType[t].keys()):
                    header += '<li><a href="#%s_%s">%s</a></li>' % (t ,b.name ,b.name)
                    body += '<a id="%s_%s"></a>' % (t ,b.name)
                    body += '<h3>%s</h3>' % b.name
                    body += htmlTableHeader(True, t)
                    body += htmlByType[t][b.name]
                    body += '</table>\n'
            header += '</ul>'
    header += '</ul>'

    return (header, body)

def generateHtmlSite(sites: Site, dateLine: datetime) -> str:
    """Generates HTML sites file

    Args:
        sites (Site): Sites to generate HTML for
        dateLine (datetime): Data update date

    Returns:
        str: Generated HTML
    """
    [header, body] = generateHtmlSiteBody(sites)
    return htmlHeader() + dateLine + header + body +htmlFooter()

def generateHtmlSiteBody(sites: Site) -> str:
    """Generate HTML site information

    Args:
        sites (Site): Sites to generate HTML for

    Returns:
        str: HTML for inclusion in a  HTML file
    """
    header = '<h1>Amateur Sites</h1>'
    body = '<h1>Amateur Sites</h1>'
    siteNames = list(sites.keys())
    siteNames.sort()
    for site in siteNames:
        header += sites[site].htmlNameLink()
    for site in siteNames:
        body += '<hr/>'
        body += sites[site].html()
    return (header, body)

def generateJs(filename: str, licences: Licence, sites: Site, links: Link,
               byLicence: bool, bySite: bool, dataDate: datetime):
    """Generate JavaScript file for online map

   Args:
        filename (str): filename to save the generated JavaScript to
        licences (Licence): licences to generate Java Script for
        sites (Site): sites to generate JavaScript for
        links (Link): links to generate JavaScript for
        byLicence (bool): if True only generate JavaScript by licence
        bySite (bool): if True only generate JavaScript by site
        dataDate (datyetime): Data update date
    """
    js = "  function setDataDate() {\n"
    js += "    updateDataDate('Data updated on %s');\n" % dataDate.strftime("%d/%m/%Y")
    js += "  }\n\n"
    if bySite:
        logging.debug('exporting javascript file %s by site' % filename)
        js += generateJsSite(sites)
    elif byLicence:
        logging.debug('exporting javascript file %s by site' % filename)
        js += generateJsLicence(licences, sites, links)
    else:
        logging.debug('exporting javascript file %s by licence and site' % filename)
        js += generateJsAll(licences, sites, links)

    f = open(filename,mode='w')
    f.write(js)
    f.close()

def generateJsAll(licences: Licence, sites: Site, links: Link) -> str:
    """Generate JavaScript content for licencses, sites and links

    Args:
        licences (Licence): licences to generate Java Script for
        sites (Site): sites to generate JavaScript for
        links (Link): links to generate JavaScript for

    Returns:
        str: JavaScript content
    """
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

def generateJsLicence(licences: Licence, sites: Site, links: Link) -> str:
    """Generate JavaScript content for licencses, sirtes and links

    Args:
        licences (Licence): licences to generate Java Script for
        sites (Site): sites to generate JavaScript for
        links (Link): links to generate JavaScript for

    Returns:
        str: JavaScript content
    """
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

def generateJsLicenceMarkersTree(licences: Licence, sites: Site,
                                 splitSubType: bool, expand: bool
                                 )-> "tuple[str, str]":
    """Generates Licence markers and the menu tree of the licence markers

    Args:
        licences (Licence): licences to generate Java Script for
        sites (Site): sites to generate JavaScript for
        splitSubType (bool): True if the sub types of licences are to be split
        expand (bool): True if the menu tree is to be expanded

    Returns:
        tuple[str, str]: menu tree and licence markers
    """
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
        if splitSubType and l.licSubType != '':
            b = b + ' ' + l.licSubType
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
                for s in LICENCE_SUB_TYPES:
                    if b.name + ' ' + s in lTypeBand[t]:
                        arrays += "    markers['%ss-%s %s'] = new Array();\n" % (t, b.name, s)
                        tree += "    tmpNode = new YAHOO.widget.TextNode('%s %s', typeNode, false);\n" % (b.name, s)
    return (arrays + markers, tree)

def generateJsSite(sites: Site) -> str:
    """Generates JavaScript for sites

    Args:
        sites (Site): Sites to generate JavaScript for

    Returns:
        str: Generated JavaScript
    """
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

def generateJsSiteMarkers(sites: Site) -> str:
    """Generates JavaScript for site markers

    Args:
        sites (Site): Sites to generate markers for

    Returns:
        str: Generated JavaScript
    """
    js = "    markers['Sites'] = new Array();\n"
    siteNames = list(sites.keys())
    siteNames.sort()
    for site in siteNames:
        js += sites[site].js()
    return js

def generateJsSiteTree() -> str:
    """Generates JavaScript root menu node for Sites

    Returns:
        str: Generated JavaScript
    """
    return "    typeNode = new YAHOO.widget.TextNode('Sites', root, false);\n"

def generateJsLinksMarkers(links: Link, splitSubType: bool) -> str:
    """Generate JavaScript for links

    Args:
        links (Link): Links to generated JavaScript for
        splitSubType (bool): True if subtypes of links are to be split out

    Returns:
        str: Generated JavaScript
    """
    js = "    links['General'] = new Array();\n"
    if splitSubType:
        for s in LICENCE_SUB_TYPES:
            js += "    links['%s'] = new Array();\n" % s
    for link in links:
        js += link.js(splitSubType)
    return js

def generateJsLinksTree(splitSubType: bool, expand: bool) -> str:
    """Generate JavaScript  menu root entries for Links

    Args:
        splitSubType (bool): True if subtypes of links are to be split out
        expand (bool): True if menu nodes are to be expanded

    Returns:
        str: Generated JavaScript
    """
    if expand:
        expand = 'true'

    else:
        expand = 'false'
    js = "    typeNode = new YAHOO.widget.TextNode('Links', root, %s);\n" % expand
    if splitSubType:
        js += "    tmpNode = new YAHOO.widget.TextNode('General', typeNode, false);\n"
        for s in LICENCE_SUB_TYPES:
            js += "    tmpNode = new YAHOO.widget.TextNode('%s', typeNode, false);\n" % s
    return js

def generateJson(filename: str, indent: int, licences: Licence, sites: Site,
                 links: Link, dataDate: datetime) -> None:
    """Generates JSON file from the given licences, sites and links

    Args:
        filename (str): File to output JSON data to
        indent (int): indent size
        licences (Licence): Licences to output
        sites (Site): Sites to output
        links (Link): links to output
        dataDate (datetime): Date data file was created
    """
    f = open(filename,mode='w')
    f.write("var dataDate = %s\n" % dataDate.strftime("%d/%m/%Y"))
    f.write("var sites = " + json.dumps(sites,default=jsonDefault, indent=indent) + '\n')
    f.write("var links = " + json.dumps(links,default=jsonDefault, indent=indent) + '\n')
    f.close()


def generateKml(filename: str, licences: Licence, sites: Site, links: Link,
                 byLicence: bool, bySite: bool, dataDate: bool,
                 outputKmz: bool=False) -> None:
    """_summary_

    Args:
        filename (str): Filename to use for KML file
        licences (Licence): list of licences
        sites (Site): list of repeater sites
        links (Link): list of inter repeater links
        byLicence (bool):  include listing of licences by licence type only
        bySite (bool):  include listing of licences by site only
        dataDate (bool): creation date for data file
        outputKmz (bool, optional): If true this file is to be included in a KMZ file. Defaults to False.
    """
    if bySite:
        logging.debug('exporting kmlfile %s by site' % filename)
        kml = generateKmlSite(sites, dataDate, outputKmz)
    elif byLicence:
        logging.debug('exporting kmlfile %s by licence' % filename)
        kml = generateKmlLicence(licences, sites, links, dataDate, 1, outputKmz=outputKmz)
    else:
        logging.debug('exporting kmlfile %s by site and licence' % filename)
        kml = generateKmlAll(licences, sites, links, dataDate, outputKmz)

    f = open(filename,mode='w')
    f.write(kml)
    f.close()

def generateKmlAll(licences: Licence, sites: Site, links: Link,
                   dataDate: datetime,  outputKmz: bool) -> str:
    """Generatre KML for licences, links and sites

    Args:
        licences (Licence): Licences to generate KML for
        sites (Site): Sites to generate KML for
        links (Link): Links to generate KML for
        dataDate (datetime): Data update date
        outputKmz (bool): True if this is for a KMZ file

    Returns:
        str: Generated KML for licences, links and sites
    """
    kml = kmlHeader()
    kml += kmlStylesLicences(outputKmz)
    kml += kmlStylesSites(outputKmz)
    kml += '    <name>Amateur Licences and Sites (data extracted %s)</name><open>1</open>\n' % dataDate.strftime("%d/%m/%Y")
    kml += '       <description>Data updated on %s</description>\n' % dataDate.strftime("%d/%m/%Y")
    kml += '    <Folder><name>Licences</name><open>1</open>\n'
    kml += '       <description>Data updated on %s</description>\n' % dataDate.strftime("%d/%m/%Y")
    kml += generateKmlLicenceBody(licences,sites,links,0,True)
    kml += '    </Folder>\n'
    kml += generateKmlLinksBody(links,True)
    kml += '    <Folder><name>Sites</name><open>0</open>\n'
    kml += '       <description>Data updated on %s</description>\n' % dataDate.strftime("%d/%m/%Y")
    kml += generateKmlSiteBody(sites)
    kml += '    </Folder>\n'
    kml += kmlFooter()
    return kml

def generateKmlLicence(licences: Licence, sites: Site, links: Link,
                       dataDate: datetime, expand: int=1,
                       splitSubType: bool=False,
                       outputKmz: bool= False) -> str:
    """Generate KML for the given licences

    Args:
        licences (Licence): Licences to generate KML for
        sites (Site): _description_
        links (Link): _description_
        dataDate (datetime): Data update date
        expand (int, optional): If 1 all items should be expanded. Defaults to 1.
        splitSubType (bool, optional): True if licence subtypes should be split for each band. Defaults to False.
        outputKmz (bool, optional): True if this is for a KMZ file. Defaults to False.

    Returns:
        str: Generated KML for licences
    """
    kml = kmlHeader()
    kml += kmlStylesLicences(outputKmz)
    kml += '    <name>Amateur Licences</name><open>1</open>\n'
    kml += '       <description>Data updated on %s</description>\n' % dataDate.strftime("%d/%m/%Y")
    kml += generateKmlLicenceBody(licences,sites,links,expand,splitSubType)
    kml += generateKmlLinksBody(links,splitSubType)
    kml += kmlFooter()
    return kml

def generateKmlLicenceBody(licences: Licence, sites: Site, links: Link,
                           expand: bool ,splitSubType: bool) -> str:
    """Generate KML for the supplied licences

    Args:
        licences (Licence): licences to generate KML for
        sites (Site): sites to include information from
        links (Link): links to include information from
        expand (int): If 1 all items should be expanded
        splitSubType (bool): True if licence subtypes should be split for each band

    Returns:
        str: _description_
    """
    def sortKey(item):
        return (licences[item].name, licences[item].frequency)

    licenceNos = sorted(list(licences.keys()), key=sortKey)
    kmlByType={}
    kml=""
    for t in LICENCE_TYPES:
        kmlByType[t]={}
    for licence in licenceNos:
        l = licences[licence]
        t = l.licType
        b = l.band()
        if splitSubType:
            for s in LICENCE_SUB_TYPES:
                if s in l.name:
                    b = b + ' ' +s
        if b not in list(kmlByType[t].keys()):
            kmlByType[t][b] = ""
        kmlByType[t][b] += licences[licence].kmlPlacemark(sites[licences[licence].site])
    for t in LICENCE_TYPES:
        if len(kmlByType[t]) > 0:
            kml += '    <Folder><name>%ss</name><open>%i</open>\n' % (t,expand)
            for b in bands:
                if b.name in list(kmlByType[t].keys()):
                    kml += '    <Folder><name>%s</name><open>0</open>\n' % b.name
                    kml += kmlByType[t][b.name]
                    kml += '    </Folder>\n'
                for s in LICENCE_SUB_TYPES:
                    if b.name + ' ' + s in list(kmlByType[t].keys()):
                        kml += '    <Folder><name>%s</name><open>0</open>\n' % (b.name + ' ' + s)
                        kml += kmlByType[t][b.name + ' ' + s]
                        kml += '    </Folder>\n'
            kml += '    </Folder>'
    return kml

def generateKmlLinksBody(links: Link, splitSubType: bool) -> str:
    """Generate KML for the supplied links

    Args:
        links (Link): Links to generate KML fro
        splitSubType (bool): True if licence subtypes should be split for each band

    Returns:
        str: KML for links
    """
    general = ''
    subTypes = {}
    if splitSubType:
        for s in LICENCE_SUB_TYPES:
            subTypes[s] = ''
    for link in links:
        if splitSubType:
            for s in LICENCE_SUB_TYPES:
                if s in link.name:
                    subTypes[s] += link.kmlPlacemark()
        else:
            general += link.kmlPlacemark()
    kml = ''
    if len(links) > 0:
        if splitSubType:
            kml += '    <Folder><name>Links</name><open>1</open>\n'
            if len(general) >0:
                kml += '    <Folder><name>General</name><open>0</open>\n'
                kml += general
                kml += '    </Folder>\n'
            for s in LICENCE_SUB_TYPES:
                if len(subTypes[s]) >0:
                    kml += '    <Folder><name>%s</name><open>0</open>\n' % s
                    kml += subTypes[s]
                    kml += '    </Folder>\n'
            kml += '    </Folder>\n'
        else:
            kml += '    <Folder><name>Links</name><open>0</open>\n'
            kml += general
            kml += '    </Folder>\n'
    return kml

def generateKmlSite(sites: Site, dataDate: datetime, outputKmz: bool) -> str:
    """Generate KML for the given sites

    Args:
        sites (Site): _description_
        dataDate (datetime): _description_
        outputKmz (bool): True if this is for a KMZ file

    Returns:
        str: KML by site
    """
    kml = kmlHeader()
    kml += kmlStylesSites(outputKmz)
    kml += '    <name>Amateur Sites</name><open>1</open>\n'
    kml += '       <description>Data updated on %s</description>\n' % dataDate.strftime("%d/%m/%Y")
    kml += generateKmlSiteBody(sites)
    kml += kmlFooter()
    return kml

def generateKmlSiteBody(sites: Site) -> str:
    """Generate KML for the suplied sites

    Args:
        sites (Site): Sites to build KML information for

    Returns:
        str: Generated KML for sites
    """
    kml = ""
    siteNames = list(sites.keys())
    siteNames.sort()
    for site in siteNames:
        kml += sites[site].kmlPlacemark()
    return kml

def generateKmz(filename: str, licences: Licence, sites: Site, links: Link,
                byLicence: bool, bySite: bool, dataDate: datetime) -> None:
    """Generates a KMZ (Google Earth) file of the selected licences, links & sites

    Args:
        filename (str): Filename to use for KMZ file
        licences (Licence): list of licences
        sites (Site): list of repeater sites
        links (Link): list of inter repeater links
        byLicence (bool): include listing of licences by licence type only
        bySite (bool): include listing of licences by site only
        dataDate (datetime): creation date for data file
    """
    logging.debug('exporting kmlfile %s' % filename)
    tempDir = tempfile.mkdtemp()
    kmlFilename = os.path.join(tempDir,'doc.kml')
    generateKml(kmlFilename, licences, sites, links, byLicence ,bySite, dataDate, True)
    archive = zipfile.ZipFile(filename,
                              mode='w',
                              compression=zipfile.ZIP_DEFLATED)
    archive.write(kmlFilename, os.path.basename(kmlFilename))
    if not bySite:
        for lt in LICENCE_TYPES:
            srcFile  = os.path.join('html',
                                    'images',
                                    LICENCE_ICON + '-' + LICENCE_COLOUR[lt] +'.png')
            destFile = 'images/' + os.path.basename(srcFile)
            archive.write(srcFile, destFile)
            srcFile  = os.path.join('html',
                                    'images',
                                    LICENCE_ICON + '-' + LICENCE_COLOUR_HI[lt] +'.png')
            destFile = 'images/' + os.path.basename(srcFile)
            archive.write(srcFile, destFile)
    if not byLicence:
        srcFile  = os.path.join('html', 'images', SITE_ICON + '-' + SITE_COLOUR +'.png')
        destFile = 'images/' + os.path.basename(srcFile)
        archive.write(srcFile, destFile)
        srcFile  = os.path.join('html', 'images', SITE_ICON + '-' + SITE_COLOUR_HI +'.png')
        destFile = 'images/' + os.path.basename(srcFile)
        archive.write(srcFile, destFile)
    archive.close()
    shutil.rmtree(tempDir)

def htmlHeader() -> str:
    header = '<html><head>'
    header += '<style type="text/css">th,td{border: 2px solid #d3e7f4;}</style>'
    header += '</head><body>'
    return header

def htmlFooter() -> str:
    """Generated HTML file footer

    Returns:
        str: HTML file footer
    """
    footer = '</body></html>'
    return footer

def htmlTableHeader(full=False, licType=T_REPEATER) -> str:
    """Generate HTML licence table header

    Args:
        full (bool, optional): if True include site information in table. Defaults to False.
        licType (str, optional): type of licence to generate table header for. Defaults to T_REPEATER.

    Returns:
        str: _description_
    """
    if licType in (T_REPEATER):
        repeater =  True
        rowspan = ' rowspan=2'
    else:
        repeater = False
        rowspan = ''
    header =  '<table><tr>'
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

def kmlStyle(styleName: str, styleIcon: str,
             styleColour: str, styleColourHl: str,
             outputKmz: bool=False):
    """Generate a KML style

    Args:
        styleName (str): Name for the style
        styleIcon (str): Icon Name
        styleColour (str): Icon colour
        styleColourHl (str): Icon colour when highlighted
        outputKmz (bool, optional): True if this is for a KMZ file. Defaults to False.
    """
    if outputKmz: styleUrl=''
    else: styleUrl='https://vhf.nz/maps/'
    return f'''
<StyleMap id="msn_{styleName}">
    <Pair>
      <key>normal</key>
      <styleUrl>#sn_{styleName}</styleUrl>
    </Pair>
    <Pair>
    <key>highlight</key>
      <styleUrl>#sh_{styleName}</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="sn_{styleName}">
      <IconStyle>
        <scale>1.1</scale>
        <Icon>
          <href>{styleUrl}images/{styleIcon}-{styleColour}.png</href>
        </Icon>
        <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
    <ItemIcon>
      <href>{styleUrl}images/{styleIcon}-{styleColour}.png</href>
    </ItemIcon>
  </ListStyle>
  </Style>
  <Style id="sh_{styleName}">
    <IconStyle>
      <scale>1.3</scale>
      <Icon>
        <href>{styleUrl}images/{styleIcon}-{styleColourHl}.png</href>
      </Icon>
      <hotSpot x="32" y="1" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <ListStyle>
      <ItemIcon>
        <href>{styleUrl}images/{styleIcon}-{styleColourHl}.png</href>
      </ItemIcon>
    </ListStyle>
  </Style>'''

def kmlHeader() -> str:
    """Generate KML file header

    Returns:
        str: KML header
    """
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    header += '<Document>\n'
    return header

def kmlStylesLicences(OutputKmz: bool=False) -> str:
    """Generate KML styles for a licences

    Args:
        outputKmz (bool, optional): True if this is for a KMZ file. Defaults to False.

    Returns:
        str: Styles for KML licences
    """
    styleText = ''
    for lt in LICENCE_TYPES:
        styleText += kmlStyle(STYLE_NAMES[lt],
                           LICENCE_ICON,
                           LICENCE_COLOUR[lt],
                           LICENCE_COLOUR_HI[lt],
                           OutputKmz)
    styleText += '''
  <Style id="repeaterLink">
    <LineStyle>
      <color>FF5AFD82</color>
      <width>4</width>
    </LineStyle>
  </Style>'''
    return styleText

def kmlStylesSites (outputKmz: bool=False) -> str:
    """Generate KML style for a site

    Args:
        outputKmz (bool, optional): True if this is for a KMZ file. Defaults to False.

    Returns:
        str: Style for KML site
    """
    return kmlStyle('site',SITE_ICON, SITE_COLOUR, SITE_COLOUR_HI, outputKmz)

def kmlFooter() -> str:
    """Generate KML file footer

    Returns:
        str: KML footer
    """
    footer = '</Document>\n'
    footer += '</kml>'
    return footer

def main() -> None:
    """Main
    """
    parser = optparse.OptionParser(usage=USAGE, version=("NZ Repeaters "+__version__))
    parser.add_option('-v','--verbose',action='store_true',dest='verbose',
                            help="Verbose logging")

    parser.add_option('-D','--debug',action='store_true',dest='debug',
                            help='Debug level logging')

    parser.add_option('-q','--quiet',action='store_true',dest='quiet',
                      help='Only critical logging')

    parser.add_option('--indent',
                      action='store',
                      type='int',
                      dest='indent',
                      default=None,
                      help="Indentation for some output formats")

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
    parser.add_option('-J','--json',
                      action='store',
                      type='string',
                      dest='jsonfilename',
                      default=None,
                      help='Output to JSON file, may be in addition to other output types')

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

    parser.add_option('-x','--xlsx',
                      action='store',
                      type='string',
                      dest='xlsxfilename',
                      default=None,
                      help='Output to xlsx file, may be in addition to other output types')

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
    parser.add_option('-S','--fixed',
                      action='store_true',
                      dest='fixed',
                      default=False,
                      help='Include fixed stations in the generated file')
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
        data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),options.datadir)

    if not os.path.isdir(data_dir):
        parser.error('Chosen data folder %s does not exist' % data_dir)

    dataDate_file = os.path.join(data_dir,'version')
    dataDate = datetime.datetime.min
    try:
        dataDate = datetime.datetime(*time.strptime(open(dataDate_file).read()[:10], "%d/%m/%Y")[0:5])
    except:
        if not options.update:
            parser.error('Can not determine data date for the chosen data folder %s' % data_dir)

    if options.update:
        updateDate = updateData(data_dir, dataDate)
        if updateDate is None:
            logging.error('Unable to update data files')
        else:
            dataDate = updateDate
    if not os.path.isfile(dataDate_file):
        logging.error('Missing data date file please update')
        exit()
    else:
        if (datetime.datetime.now() - dataDate) > datetime.timedelta(weeks=4):
            print('the additional data files are more than 4 weeks old so it is recommended that you update using -u')

    generationDate = datetime.datetime.now()

    callsigns_file = os.path.join(data_dir,'callsigns.csv')
    ctcss_file = os.path.join(data_dir,'ctcss.csv')
    licences_file = os.path.join(data_dir,'prism.sqlite')
    links_file = os.path.join(data_dir,'links.csv')
    info_file = os.path.join(data_dir,'info.csv')
    skip_file = os.path.join(data_dir,'skip.csv')

    if options.htmlfilename == None and\
       options.jsfilename == None and\
       options.jsonfilename == None and\
       options.kmlfilename == None and\
       options.kmzfilename == None and\
       options.csvfilename == None and\
       options.xlsxfilename == None and\
       not options.update:
        parser.error('Atleast one output file type must be defined or no output will be generated')

    if options.allTypes:
        options.beacon = True
        options.digi = True
        options.fixed = True
        options.repeater = True
        options.tv = True

    if not (options.beacon or options.digi or options.fixed or options.repeater or options.tv):
        if options.update:
            exit()
        else:
            parser.error('Atleast one of the -a -b ,-d, -r -t or -x options must be specified for output to be generated.')

    if not (options.minFreq == None or options.maxFreq == None):
        if options.minFreq > options.maxFreq:
            parser.error('The maximum frequency must be greater than the minimum frequency.')

    if options.licence and options.site:
        parser.error('Only one of site or licence may be specified')
    elif not (options.licence or options.site):
        print('Neither site or licence output specified creating output including licence and site')

    callsigns = readTextCsv(callsigns_file)
    ctcss = readCtcss(ctcss_file)
    info = readRowCsv(info_file,6)
    skip = readRowCsv(skip_file,3)
    #sites, licences, licensees = readLicences(licences_file,callsigns,ctcss, TODO: Tidy up
    sites, licences, licensees = getLicenceInfo(callsigns,ctcss,
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

    if options.xlsxfilename != None:
        generateXlsx(options.xlsxfilename, licences, sites)

    if options.htmlfilename != None:
        generateHtml(options.htmlfilename, licences, sites, links, options.licence, options.site, generationDate)

    if options.jsfilename != None:
        generateJs(options.jsfilename, licences, sites, links, options.licence, options.site, generationDate)

    if options.jsonfilename != None:
        generateJson(options.jsonfilename, options.indent, licences, sites, links, generationDate)

    if options.kmlfilename != None:
        generateKml(options.kmlfilename, licences, sites, links, options.licence, options.site, generationDate)

    if options.kmzfilename != None:
        generateKmz(options.kmzfilename, licences, sites, links, options.licence, options.site, generationDate)

def updateData(dataFolder: str, localDate: datetime):
    """Updates the local data for the application from the internet if the files on
    the internet are newer than the local copy.

    Args:
        dataFolder (str): folder to place downloaded data files in
        localDate (datetime): date of the existing data files (or None if it does not exist)

    Returns:
        datetime: Date of updated datafiles or None if data update unsusesful
    """
    try:
        f = urllib.request.urlopen(UPDATE_URL + 'version')
        remoteDate = datetime.datetime(*time.strptime(f.read(10).decode('utf-8'), "%d/%m/%Y")[0:5])
        if localDate >= remoteDate:
            print('Data already up to date, continuing without downloading data')
            return (localDate)
        urlDownload(UPDATE_URL + 'data.zip', dataFolder)
        z = zipfile.ZipFile(os.path.join(dataFolder,'data.zip'))
        z.extractall(dataFolder)
        f = open(os.path.join(dataFolder,'version'),'w')
        f.write(remoteDate.strftime("%d/%m/%Y"))
        f.close()
        return(remoteDate)
    except:
        return(None)

def urlDownload(url: str, folder: str=None, fileName: str=None) -> None:
    """Download a file from the given URL and save to the given folder and file name.
    If no filename is given use the filename from the url and if no folder is given use the current folder

    Args:
        url (str): URL to download form
        folder (str, optional): Folder to download to. Defaults to None.
        fileName (str, optional): File to download to. Defaults to None.
    """
    if fileName == None:
        fileName = url.split('/')[-1]
    if folder != None:
        fileName = os.path.join(folder, fileName)
    u = urllib.request.urlopen(url)
    f = open(fileName, 'wb')
    fileSize = int(u.headers["Content-Length"])
    print("Downloading: %s Bytes: %s" % (fileName, fileSize))

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
        print(status, end=' ')
    f.close()

if __name__ == "__main__":
    main()
