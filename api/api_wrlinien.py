import requests
from requests import RequestException, HTTPError

from utils import get_config, get_logger
import time

logger = get_logger(__name__)


class WrLinienApiException(Exception):
    pass


class WrLinienApi:
    """
    Get updates to stations from wienerlinien.at API and parse to a `dict`, then cache the `dict` as `self.data`

    Input:
    Uses data from `config.json` with the following keys:
        wrlinien (json):                        wrlinien json with the following keys:
            updateInterval (number):            minimum of how long until the next API call should be made in seconds
            key (str):                          Wiener Linien API key
            rbls (array[number]):               rbls (ids) of stations

    Output:
    self.data: `None` or `dict` with the following keys:
        stations (array[dict]):             array with data to stations
            name (str):                    name of station, used to merge with other traffic data
            lines (array[dict]):            array of transport lines of type `dict` with the following keys:
                direction (str):            displayed name of direction/destination the train is heading
                departures (array[int]):    array of departure countdowns in minutes of type `int`
                barrierFree (bool):         `True` if the coming transport is barrier free accessible
                name (str):                 lines name abbreviated to 3 `char`s
                trafficJam (bool):          `True` if the coming transport is delayed
        lastUpdate (time.struct_time):  server timestamp of update

    Example self.data:
    {
        'stations': [
            {
                'name': 'Engerthstraße/Traisengasse',
                'lines': [
                    {'direction': 'Friedrich-Engels-Platz', 'departures': [0, 9, 18, 28, 38, 48, 58, 68], 'barrierFree': True, 'name': '11B', 'trafficJam': False},
                    {'direction': 'Bhf. Heiligenstadt S U', 'departures': [6, 13, 22, 32, 42, 52, 62], 'barrierFree': True, 'name': '11A', 'trafficJam': False},
                    {'direction': 'Griegstraße', 'departures': [2, 12, 21, 31, 41, 51, 61], 'barrierFree': True, 'name': ' 5A', 'trafficJam': False},
                ]
            }, {
                'name': 'Traisengasse',
                'lines': [
                    {'direction': 'Dornbach', 'departures': [4, 15, 25, 35, 45, 55, 65], 'barrierFree': True, 'name': '  2', 'trafficJam': False}
                ]
            }
        ],
        'lastUpdate': time.struct_time(...)
    }
    """

    def __init__(self):
        self.data = None
        self.nextUpdate = 0

    def update(self):
        """
        Updates self.data iff an update is needed, else does nothing
        """
        if self.nextUpdate <= time.time():
            self._get_data()
            conf = get_config()
            self.nextUpdate = time.time() + conf['api']['wrlinien']['updateInterval']

    @staticmethod
    def _merge_stations_by_name(result):
        stations = []
        for s in result:
            exists = False
            for d in stations:
                if s['name'] == d['name']:
                    d['lines'].extend(s['lines'])
                    exists = True
            if exists is False:
                stations.append(s)
        return stations

    def _get_data(self):
        self.data = None
        conf = get_config()
        try:
            res = requests.get('https://www.wienerlinien.at/ogd_realtime/monitor?rbl=%s&sender=%s'
                               % (','.join(map(str, conf['api']['wrlinien']['rbls'])), conf['api']['wrlinien']['key']))
        except RequestException or HTTPError:  # retry on error
            logger.error("Caught RequestException")
            res = requests.get('https://www.wienerlinien.at/ogd_realtime/monitor?rbl=%s&sender=%s'
                               % (','.join(map(str, conf['api']['wrlinien']['rbls'])), conf['api']['wrlinien']['key']))
        res.raise_for_status()
        api_data = res.json()

        if api_data['message']['value'] != 'OK':  # check if server sends OK
            logger.error('[WRL]: NOK. %s' % api_data)
            error_msg = "API returns NOK. Please check the message and the API Key."
            raise WrLinienApiException(error_msg)

        # parse to wrlinien dict
        translated_result = []
        for a_s in api_data['data']['monitors']:
            station = {
                'lines': [],
                'name': a_s['locationStop']['properties']['title'],
            }
            for a_s_l in a_s['lines']:
                line = {
                    'name': a_s_l['name'].rjust(3),
                    'direction': a_s_l['towards'],
                    'barrierFree': a_s_l['barrierFree'],
                    'trafficJam': a_s_l['trafficjam'],
                    'departures': []
                }
                for d in a_s_l['departures']['departure']:
                    if d['departureTime']:
                        line['departures'].append(d['departureTime']['countdown'])
                station['lines'].append(line)
            translated_result.append(station)

        wrlinien_data = {
            'stations': self._merge_stations_by_name(translated_result),
            'lastUpdate': time.strptime(api_data['message']['serverTime'], '%Y-%m-%dT%H:%M:%S.%f%z')
        }
        logger.info("retrieved data: %s" % wrlinien_data)
        self.data = wrlinien_data
