import requests
from requests import RequestException, HTTPError

from utils import get_config, get_logger
import xml.etree.ElementTree as ET
import time

logger = get_logger(__name__)


class CitybikeWienApi:
    """
    Get updates to stations from citybikewien.at API and parse to an `array` of `dict`s,
    then cache the `array` as `self.data`

    Input:
    Uses data from `config.json` with the following keys:
        citybikewien (json, optional):                citybikewien json with the following keys:
            updateInterval (number):        minimum of how long until the next API call should be made in seconds
            stations (array[json]):         json with station ids and values
                id (number):                id of station
                rename (str, optional):     do not use the api name of the station and use this value instead

    Output:
    self.data: `None` or `array` with items of `dict` with the following keys:
        id (int):       id of the station
        status (str):   status code of station from citybikewien.at API
        name (str):     name of station, used to merge with other traffic data
        bikes (int):    number of available bikes at station

    Example self.data:
    [
        {'id': '2005', 'status': 'aktiv', 'name': 'Handelskai', 'bikes': '2'},
        {'id': '2004', 'status': 'aktiv', 'name': 'Traisengasse', 'bikes': '0'}
    ]
    """

    def __init__(self):
        self.data = None  # fetched data
        self.nextUpdate = 0  # time when next update can be done in seconds since the Epoch

    def update(self):
        """
        Updates self.data iff an update is needed, else does nothing
        """
        conf = get_config()
        if 'citybikewien' not in conf['api']:  # optional citybikewien
            logger.info("No citybikewien specified, skipping citybikewien api update()")
            self.data = []
            return
        if self.nextUpdate <= time.time():  # only update when needed
            self._get_data()
            self.nextUpdate = time.time() + conf['api']['citybikewien']['updateInterval']

    def _get_data(self):
        try:
            res = requests.get('http://dynamisch.citybikewien.at/citybike_xml.php')
        except RequestException or HTTPError:  # retry on error
            logger.error("Caught RequestException")
            res = requests.get('http://dynamisch.citybikewien.at/citybike_xml.php')
        res.raise_for_status()
        root = ET.fromstring(res.text)
        citybikewien_data = []

        # extract only wanted stations and parse to citybikewien dict
        conf = get_config()
        stations = conf['api']['citybikewien']['stations']
        for station_xml in root.findall('station'):
            if station_xml.find('id').text in list(map(lambda s: str(s['id']), stations)):
                citybikewien_data.append({
                    'id': station_xml.find('id').text,
                    'name': station_xml.find('name').text,
                    'bikes': station_xml.find('free_bikes').text,
                    'status': station_xml.find('status').text
                })

        # rename stations to names from config, so they can be mapped with other api data by name
        for conf_station in stations:
            if 'rename' in conf_station:
                for station in citybikewien_data:
                    if station['id'] == str(conf_station['id']):
                        station['name'] = conf_station['rename']
                        break

        logger.info("updated data: %s" % citybikewien_data)
        self.data = citybikewien_data
