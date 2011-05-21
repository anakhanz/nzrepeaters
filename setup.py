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

from distutils.core import setup
import sys
if sys.platform[:3] == 'win':
    import py2exe

from repeaters.repeaters import __version__

LONG_DESCRIPTION="""A tool to generate listings of NZ Amateur radio Beacons, Digipeaters and Repeaters from the data published by the `RSM Smart system <http://www.rsm.govt.nz/smart-web/smart/page/-smart/WelcomePage.wdk>`_

Currently it generates output in the following formats:
 * KML - for display in Google Maps or Google Earth
 * KMZ - for display in Google Maps or Google Earth
 * CSV

An example of the maps in action can be found on the `Wellington VHF Group website at <http://www.vhf.org.nz/>`_ http://www.vhf.org.nz/maps"""

setup(name = 'NZ_Repeaters',
      version = __version__,
      author = 'Rob Wallace ZL2WAL',
      author_email = 'rob@wallace.gen.nz',
      maintainer = 'Rob Wallace ZL2WAL',
      maintainer_email = 'rob@wallace.gen.nz',
      url="http://projects.wallace.gen.nz/projects/nzrepeaters",
      description = 'NZ Anateur Repeater information list/map builder',
      long_description = LONG_DESCRIPTION,
      download_url = 'http://projects.wallace.gen.nz/projects/nzrepeaters/files',
      # classifiers see http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Utilities'],
      license = 'GPL-2',
      packages = ['repeaters', 'mapping'],
      scripts = ['rpt'],
      package_data={'repeaters': ['data/*.csv','data/*.sqlite']},
      console=['repeaters/repeaters.py','rpt'],
      options={'py2exe':{'includes':['repeaters', 'mapping']}})