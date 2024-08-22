# -*- coding: UTF-8 -*-

## NZ Repeater list/map builder
## URL: https://github.com/anakhanz/nzrepeaters
## Copyright (C) 2024, Rob Wallace rob[at]wallace[dot]kiwi
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

import requests
import json
import logging

from .common import rsmBaseUrl, rsmHeaders

# Valid Licence Statuses
LICENCE_STATUSES = ("All",
                    "Cancelled",
                    "Certificate Expired",
                    "Current",
                    "Declined",
                    "Expired",
                    "Incomplete",
                    "Payment Processing",
                    "Planned")

AMATEUR_TYPE_CODES = ("H1", # Amateur Repeater
                      "H2", # Amateur Beacon
                      "H3", # Amateur Digipeater
                      "H4", # Amateur Fixed
                      "H9", # Amateur TV Repeater
                      "HM", # Amateur Repeater - Mobile Transmit
                      )

GRID_DEFAULT_OPTS = ("TOPO50_T",
                     "NZMS260_METRIC_M",
                     "LAT_LONG_NZGD2000_D2000",
                     "LAT_LONG_NZGD1949_D",
                     "NZMG_LONG_REF_L",
                     "NZTM2000_TM2000")

SORT_OPTIONS = ("Licence ID",
                "LicenceNumber",
                "licensee",
                "channel",
                "frequency",
                "location",
                "gridRefDefault",
                "licenceType",
                "status",
                "suppressed")



def getLicences(page: int = 1, pageSize: int = 200,
                 sortBy: str = None,
                 sortAscending: bool = True,
                 searchText: str = None,
                 txLocation: str = None,
                 rxLocation: str = None,
                 location: str = None,
                 district: str = None,
                 callSign: str = None,
                 channel: str = None,
                 tx: bool = True, rx: bool = False,
                 exactFrequency: bool = True,
                 fromFrequency: float = None,
                 toFrequency: float = None,
                 statusCurrent: bool = True,
                 statusExpired: bool = False,
                 statusCancelled: bool = False,
                 licenceType: str = None,
                 gridRef: str = None,
                 radius: float = None,
                 associatedLicences: bool = False,
                 gridRefDefault: str = None) -> dict:
    """Get licences from the RSM database one page at a time

    Args:
        page (int, optional): The page in the collection to get. Defaults to 1.
        pageSize (int, optional): The number of items to include in each page. Defaults to 200.
        sortBy (str, optional): Name of the field to sort the response by. Defaults to None.
        sortAscending (bool, optional): Whether to sort the response in ascending or descending order (False). Defaults to True.
        searchText (str, optional): The text string to search for. Free-text search across licence number, licence ID, licensee name, client number, NZBN, or application number. Defaults to None.
        txLocation (str, optional): The name of the Location, or part thereof. Multiple locations should be separated by commas,e.g. tower, mast.. Defaults to None.
        rxLocation (str, optional): The name of the Location, or part thereof. Multiple locations should be separated by commas,e.g. tower, mast.. Defaults to None.
        location (str, optional): Location name or location ID. Defaults to None.
        district (str, optional): Licence district. Defaults to None.
        callSign (str, optional): Licence callsign. Defaults to None.
        channel (str, optional): Frequency channel. Defaults to None.
        tx (bool, optional): Include transmitt licences. Defaults to True.
        rx (bool, optional): Include recieve licences. Defaults to False.
        exactFrequency (bool, optional): Exact match for frequency search. Defaults to True.
        fromFrequency (float, optional): Start frequency of licence the search. If no “toFrequency” specified, API only response licence on this single frequency.. Defaults to None.
        toFrequency (float, optional): Stop frequency of licence the search. Defaults to None.
        statusCurrent (bool, optional): Include current licences. Defaults to True.
        statusExpired (bool, optional): Include expired Licences. Defaults to False.
        statusCancelled (bool, optional): Include cancelled licences. Defaults to False.
        licenceType (str, optional): Licence type to search for. Defaults to None.
        gridRef (str, optional): Grid reference to search around. Defaults to None.
        radius (float, optional): Radius around GridRef for area search in km. Defaults to None.
        associatedLicences (bool, optional): Include associated licences. Defaults to False.
        gridRefDefault (str, optional): Select the returned gridref format. Defaults to None.

    Returns:
        dict: JSON response object
    """

    url = rsmBaseUrl + '/licences'
    params = {'page': page,
              'page-size': pageSize}
    if sortBy:
        assert sortBy in SORT_OPTIONS
        params['sort-by'] = sortBy
    if sortAscending: params['sort-order'] = 'asc'
    else: params['sort-order'] = 'desc'
    if searchText: params['search'] = searchText
    if txLocation: params['transmitlocation'] =txLocation
    if rxLocation: params['receivelocation'] = rxLocation
    if location: params['location'] = location
    if district: params['district'] = district
    if callSign: params['callSign'] = callSign
    if channel: params['channel'] = channel
    if tx and not rx: params['txRx'] = 'TRN'
    elif not tx and rx: params['txRx'] = 'RCV'
    else: params['txRx'] = 'TRN,RCV'
    params['exactMatchFreq'] = int(exactFrequency)
    if fromFrequency:
        params['fromFrequency'] = fromFrequency
        if toFrequency:
            assert toFrequency >= fromFrequency
            if toFrequency > fromFrequency:
                params['toFrequency'] = toFrequency
    assert statusCurrent or statusExpired or statusCancelled
    params['licenceStatus'] = []
    if statusCurrent: params['licenceStatus'].append('Current')
    if statusExpired: params['licenceStatus'].append('Expired')
    if statusCancelled: params['licenceStatus'].append('Cancelled')
    if licenceType:
        if type(licenceType) is str: assert licenceType in AMATEUR_TYPE_CODES # TODO: add other type codes
        if type(licenceType) in (tuple, list):
            for t in licenceType: assert t in AMATEUR_TYPE_CODES
        params['licenceTypeCode'] = licenceType
    if gridRef and radius:
        params['GridRef'] = gridRef
        params['radius'] = radius
    params['includeAssociatedLicences'] = int(associatedLicences)
    if gridRefDefault:
        assert gridRefDefault in GRID_DEFAULT_OPTS
        params['gridRefDefault'] = gridRefDefault

    response = requests.get(url, headers=rsmHeaders, params=params)
    logging.info(response.url)
    response.raise_for_status()

    return response.json()

def getLicence(licenceId: int, gridRefDefault: str = None) -> dict:
    """Get licence details for the given licenceId fromthe RSM database

    Args:
        licenceId (int): _description_
        gridRefDefault (str, optional): Select the returned gridref format. Defaults to None.

    Returns:
        dict: Licence JSON response
    """
    url = rsmBaseUrl + f'/licences/' + str(licenceId)
    params = {}
    if gridRefDefault:
        assert gridRefDefault in GRID_DEFAULT_OPTS
        params['gridRefDefault'] = gridRefDefault

    response = requests.get(url, headers=rsmHeaders, params=params)
    logging.info(response.url)
    response.raise_for_status()

    return response.json()

def getLicenceList(sortBy: str = None,
                   sortAscending: bool = True,
                   searchText: str = None,
                   txLocation: str = None,
                   rxLocation: str = None,
                   location: str = None,
                   district: str = None,
                   callSign: str = None,
                   channel: str = None,
                   tx: bool = True, rx: bool = False,
                   exactFrequency: bool = True,
                   fromFrequency: float = None,
                   toFrequency: float = None,
                   statusCurrent: bool = True,
                   statusExpired: bool = False,
                   statusCancelled: bool = False,
                   licenceType: str = None,
                   gridRef: str = None, #
                   radius: float = None,
                   associatedLicences: bool = False,
                   gridRefDefault: str = None):
    """Get a list of licences from the RSM database.

    Args:
        sortBy (str, optional): Name of the field to sort the response by. Defaults to None.
        sortAscending (bool, optional): Whether to sort the response in ascending or descending order (False). Defaults to True.
        searchText (str, optional): The text string to search for. Free-text search across licence number, licence ID, licensee name, client number, NZBN, or application number. Defaults to None.
        txLocation (str, optional): The name of the Location, or part thereof. Multiple locations should be separated by commas,e.g. tower, mast.. Defaults to None.
        rxLocation (str, optional): The name of the Location, or part thereof. Multiple locations should be separated by commas,e.g. tower, mast.. Defaults to None.
        location (str, optional): Location name or location ID. Defaults to None.
        district (str, optional): Licence district. Defaults to None.
        callSign (str, optional): Licence callsign. Defaults to None.
        channel (str, optional): Frequency channel. Defaults to None.
        tx (bool, optional): Include transmitt licences. Defaults to True.
        rx (bool, optional): Include recieve licences. Defaults to False.
        exactFrequency (bool, optional): Exact match for frequency search. Defaults to True.
        fromFrequency (float, optional): Start frequency of licence the search. If no “toFrequency” specified, API only response licence on this single frequency.. Defaults to None.
        toFrequency (float, optional): Stop frequency of licence the search. Defaults to None.
        statusCurrent (bool, optional): Include current licences. Defaults to True.
        statusExpired (bool, optional): Include expired Licences. Defaults to False.
        statusCancelled (bool, optional): Include cancelled licences. Defaults to False.
        licenceType (str, optional): Licence type to search for. Defaults to None.
        gridRef (str, optional): Grid reference to search around. Defaults to None.
        radius (float, optional): Radius around GridRef for area search in km. Defaults to None.
        associatedLicences (bool, optional): Include associated licences. Defaults to False.
        gridRefDefault (str, optional): Select the returned gridref format. Defaults to None.

    Returns:
        _type_: List of the licences
    """
    page=0
    pageSize=200
    numPages = 1
    licences = []
    while page < numPages:
        page += 1
        response = getLicences(page, pageSize, sortBy, sortAscending,
                               searchText,
                               txLocation, rxLocation, location, district,
                               callSign, channel, tx, rx,
                               exactFrequency, fromFrequency, toFrequency,
                               statusCurrent, statusExpired,
                               statusCancelled, licenceType,
                               gridRef, radius,
                               associatedLicences, gridRefDefault)
        if page == 1: numPages = response['totalPages']
        licences += response['items']
    return licences