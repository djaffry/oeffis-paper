import random
import string
import requests
import time

from requests import RequestException, HTTPError

from utils import get_config, get_logger

logger = get_logger(__name__)

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'
def _gen_rnd_str(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


class OeBBApi:
    """
    Get updates to stations from tickets.oebb.at API and parse to an `array` of `dict`s,
    then cache the `array` as `self.data`

    Input:
    Uses data from `config.json` with the following keys:
        oebb (json):                            oebb json with the following keys:
            updateInterval (number):            minimum of how long until the next API call should be made in seconds
            connections (array[json]):          array of train connections
                from (int):                     id of the departure station
                to (int):                       id of the destination station
            rename (array[json], optional):     array of stations to be renamed
                old (str):                      old name to be renamed
                new (str):                      old name station renamed to this value

    Output:
    self.data: `None` or `array` with items of `dict` with the following keys:
        name (str):                    name of station, used to merge with other traffic data
        lines (array[dict]):            array of transport lines of type `dict` with the following keys:
            direction (str):            displayed name of direction/destination the train is heading
            departures (array[int]):    array of departure countdowns in minutes of type `int`
            barrierFree (bool):         `True` if the coming train is barrier free accessible
            name (str):                 lines name in a 3`char` long representation
            trafficJam (bool):          `True` if the coming train is delayed

    Example self.data:
    [
        {'name': 'Handelskai', 'lines': [
            {'direction': 'nach Floridsdorf', 'departures': [8, 11], 'barrierFree': True, 'name': '  S', 'trafficJam': False}
        ]},
        {'name': 'Traisengasse', 'lines': [
            {'direction': 'nach Meidling', 'departures': [2, 14, 17, 17, 24], 'barrierFree': True, 'name': '  S', 'trafficJam': False},
            {'direction': 'nach Flughafen', 'departures': [8], 'barrierFree': True, 'name': '  S', 'trafficJam': False}
        ]}
    ]
    """

    def __init__(self):
        self.exc_info = None  # exception for main thread
        self.data = None  # fetched data
        self.nextUpdate = 0   # time when next update can be done in seconds since the Epoch
        self.session_end = 0  # time when the session expires in seconds since the Epoch
        self.header = ""  # header for requests

    def reset(self):
        self.__init__()

    def update(self):
        """
        Updates self.data iff an update is needed, else does nothing
        """
        try:
            if self.nextUpdate <= time.time():  # only update when needed
                self._get_data()
                conf = get_config()
                self.nextUpdate = time.time() + conf['api']['oebb']['updateInterval']
        except Exception as err:
            import sys
            self.exc_info = sys.exc_info()

    def _new_session(self):
        self.header = {'Channel': 'inet', 'User-Agent': user_agent}
        try:
            res = requests.get('https://tickets.oebb.at/api/domain/v3/init',
                               headers=self.header,
                               params={'userId': 'anonym-%s-%s-%s' % (_gen_rnd_str(8), _gen_rnd_str(4), _gen_rnd_str(2))})
        except RequestException or HTTPError:  # retry on error
            res = requests.get('https://tickets.oebb.at/api/domain/v3/init',
                               headers=self.header,
                               params={'userId': 'anonym-%s-%s-%s' % (_gen_rnd_str(8), _gen_rnd_str(4), _gen_rnd_str(2))})
        res.raise_for_status()
        auth = res.json()
        logger.debug('autenticated: %s' % auth)
        self.header.update(
            {'AccessToken': auth['accessToken'], 'SessionId': auth['sessionId'], 'x-ts-supportid': auth['supportId']})
        self.session_end = time.time() + auth['sessionTimeout']

    def _get_header(self):
        """
        creates new header when session is expired
        :return: updated self.header
        """
        if time.time() > self.session_end - 1000:
            self._new_session()
        return self.header

    @staticmethod
    def _replace_station_and_direction_names(stations):
        conf = get_config()
        if 'rename' in conf['api']['oebb']:
            for station in stations:
                for rename in conf['api']['oebb']['rename']:
                    for line in station['lines']:
                        if line['direction'] == rename['old']:
                            line['direction'] = rename['new']
                    if station['name'] == rename['old']:
                        station['name'] = rename['new']
        return stations

    @staticmethod
    def _merge_stations_by_name(unmerged_stations):
        stations = []
        for unmerged_station in unmerged_stations:
            exists = False
            for station in stations:
                if unmerged_station['name'] == station['name']:
                    station['lines'].extend(unmerged_station['lines'])
                    exists = True
            if exists is False:
                stations.append(unmerged_station)
        return stations

    @staticmethod
    def _merge_lines_by_direction(unmerged_stations):
        stations = []
        for unmerged_station in unmerged_stations:
            lines = []
            for unmerged_line in unmerged_station['lines']:
                exists = False
                for line in lines:
                    # if unmerged_line['name'] == line['name'] and
                    #   unmerged_line['direction'] == line['direction']:  # merge trains by name and direction
                    if unmerged_line['direction'] == line['direction']:  # merge trains by direction only
                        line['departures'].extend(unmerged_line['departures'])
                        exists = True
                if exists is False:
                    lines.append(unmerged_line)
            for line in lines:
                line['departures'].sort()
            stations.append({'lines': lines, 'name': unmerged_station['name']})
        return stations

    @staticmethod
    def _extract_line_and_calc_countdown(connection):
        line = {
            # 'name': data['sections'][0]['category']['displayName'].rjust(3),  # alternative name
            'name': connection['sections'][0]['category']['shortName'].rjust(3),
            'direction': connection['sections'][0]['to']['name'],
            'barrierFree': 'disabled' in connection['sections'][0]['category']['journeyPreviewIconId'],
            'trafficJam': 'departureDelay' in connection['sections'][0]['from']
        }
        if line['trafficJam']:  # if there is a delay, use departureDelay value instead
            departure_time = time.strptime(connection['sections'][0]['from']['departureDelay'][:-3], "%Y-%m-%dT%H:%M:%S.")
        else:
            departure_time = time.strptime(connection['sections'][0]['from']['departure'][:-3], "%Y-%m-%dT%H:%M:%S.")
        countdown = round((time.mktime(departure_time) - time.mktime(time.localtime())) / 60)
        line['departures'] = [max(0, countdown)]
        station = {'lines': [line], 'name': connection['sections'][0]['from']['name']}
        return station

    def _get_data(self):
        self.data = None
        conf = get_config()

        request_data = {  # oebb api request
            "reverse": False,
            "datetimeDeparture": None,
            "filter": {
                "regionaltrains": False,
                "direct": False,
                "changeTime": False,
                "wheelchair": False,
                "bikes": False,
                "trains": False,
                "motorail": False,
                "droppedConnections": False
            },
            "passengers": [
                {
                    "type": "ADULT",
                    "me": False,
                    "remembered": False,
                    "challengedFlags": {
                        "hasHandicappedPass": False,
                        "hasAssistanceDog": False,
                        "hasWheelchair": False,
                        "hasAttendant": False
                    },
                    "relations": [],
                    "cards": [],
                    "birthdateChangeable": True,
                    "birthdateDeletable": True,
                    "nameChangeable": True,
                    "passengerDeletable": True
                }
            ],
            "count": 5,
            "from": {
                "number": None
            },
            "to": {
                "number": None
            },
        }

        stations = []
        for conf_connection in conf['api']['oebb']['connections']:
            request_data['from']['number'] = conf_connection['from']
            request_data['to']['number'] = conf_connection['to']
            request_data['datetimeDeparture'] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            try:
                res = requests.post('https://tickets.oebb.at/api/hafas/v4/timetable',
                                    headers=self._get_header(),
                                    json=request_data)
            except RequestException or HTTPError:  # retry on error
                logger.error("Caught RequestException")
                res = requests.post('https://tickets.oebb.at/api/hafas/v4/timetable',
                                    headers=self._get_header(),
                                    json=request_data)
            res.raise_for_status()
            connections = res.json()['connections']

            for connection in connections:
                if connection['switches'] > 0:  # skip if not a direct connection
                    break
                if connection['sections'][0]['category']['name'].lower() == 's' or \
                        connection['sections'][0]['category']['name'].lower() == 'r':  # only trains
                    stations.append(self._extract_line_and_calc_countdown(connection))
                # else:
                # logger.warning("[OeBB]: Other category found: %s" % connection['sections'][0]['category'])

        renamed_stations = self._replace_station_and_direction_names(stations)
        premerged_stations = self._merge_stations_by_name(renamed_stations)
        oebb_data = self._merge_lines_by_direction(premerged_stations)

        logger.info("retrieved data: %s" % oebb_data)
        self.data = oebb_data
