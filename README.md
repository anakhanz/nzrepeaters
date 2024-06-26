# NZ Repeaters Listing Generator

## Introduction

This program generates listings of the NZ Amateur Radio Beaacons, digipeaters
and Repeaters fromt he information published by the [RSM SMART system](http://www.rsm.govt.nz/smart-web/smart/page/-smart/WelcomePage.wdk).

Currently it outputs the data in the following formats:

* KML - for display in Google earth and Google maps
* KML - for display in Google earth and Google maps
* CSV - Comma seperated variable spreadsheet format

An example of the maps in action can be found on the [Wellington VHF Group
website](http://www.vhf.org.nz/maps)

## Data sources

The data included with this software comes from two sources:

The technical data is sourced form the RSM's SMART system, if this is
incorrect please notify the owner of the licence and ask them to submit
a form 10 to get it corrected (Note: if the licencee is NZART please
contact the branch not NZART itself).  The actual data from SMART is as
follows:

* Frequency (the input frequency for repeaters is calculated)
* Type
* Site Name
* Map Reference
* Coordinates
* Licence Number
* Licencee

Other data is sourced from the NZART call book for corrections to this
data please email <zl2wal@vhf.nz>, this is:

* Callsign
* CTCSS
* Branch
* Trustees
* Notes

### Updating the data files

An updated data file is made available every week on thursday mornings,
and can be fetched by the program using the following command:

```bash
rpt -u
```

## Installation

### Windows

For installation on windows please download the latest windows installer and execute it, this will install the software and add it to the windows path so that it may be run from the command line.

### Linux and other

For other platforms this requires that python 2.6 or later is installed
including distutils, to perform the actual installation use the following
commands to install the software once you have downloaded the source
package:

```bash
  tar -xvzf NZ_Repeaters-*.tar.gz
  cd NZ_Repeaters-*
  ./setup.py install
```

## Usage

```text
rpt [options]
```

Options:

```text
- `--version` - show program's version number and exit
- `-h, --help` - show this help message and exit
- `-v, --verbose` - Verbose logging
- `-D, --debug` - Debug level logging
- `-q, --quiet` - Only critical logging
- `--indent=INDENT` - Indentation for some output formats
- `-H HTMLFILENAME, --html=HTMLFILENAME` - Output to html file, may be in addition to other output types
- `-j JSFILENAME, --javascript=JSFILENAME` - Output to javascript file, may be in addition to other output types
- `-J JSONFILENAME, --json=JSONFILENAME` - Output to JSON file, may be in addition to other output types
- `-k KMLFILENAME, --kml=KMLFILENAME` - Output to kml file, may be in addition to other output types
- `-z KMZFILENAME, --kmz=KMZFILENAME` - Output to kmz file, may be in addition to other output types
- `-c CSVFILENAME, --csv=CSVFILENAME` - Output to csv file, may be in addition to other output types
- `-s, --site` - Output information by site
- `-l, --licence` - Output information by licence
- `-b, --beacon` -  Include digipeaters in the generated file
- `-d, --digi` - Include digipeaters in the generated file
- `-r, --repeater` -  Include digipeaters in the generated file
- `-t, --tv` -  Include digipeaters in the generated file
- `-a, --all` - Include all types in the generated file
- `-f MINFREQ, --minfreq=MINFREQ` - Filter out all below the specified frequency
- `-F MAXFREQ, --maxfreq=MAXFREQ` - Filter out all above the specified frequency
- `-i INCLUDE, --include=INCLUDE` - Filter licences to only include licences that contain [include] in their name
- `-e EXCLUDE, --exclude=EXCLUDE` - Filter licences to exclude licences that contain [exclude] in their name
- `-B BRANCH, --branch=BRANCH` - Filter licences to only include those from the selected branch
- `-u, --update` - Update data files from the Internet
- `-A DATADIR, --datafolder=DATADIR` - Modify the data folder location from the default
```

## Graphics

The icons used in the maps are supplied by Maps Icons Collection <https://mapicons.mapsmarker.com> under the Creative Commons Attribution-Share Alike 3.0 Unported license (CC BY SA 3.0) which lets you remix, tweak, and build upon our work even for commercial reasons, as long as you credit the project and license your new creations under the identical terms.
