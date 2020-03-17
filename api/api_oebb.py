import time
import subprocess
import json
import os

from utils import get_config, get_logger

logger = get_logger(__name__)


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
        self.nextUpdate = 0  # time when next update can be done in seconds since the Epoch
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

    def _get_data(self):
        self.data = None
        conf = get_config()

        res_stations = []
        for c in conf['api']['oebb']['connections']:
            res_bytes = subprocess.check_output(
                ["node", os.path.dirname(os.path.abspath(__file__)) + "/../lib/node/oebb-journeys.js", str(c['from']), str(c['to'])],
                shell=False)
            journey_data = json.loads(res_bytes.decode("utf-8").replace("'", '"'))
            res_stations.append(journey_data)

        oebb_data = []
        for r_s in res_stations:
            station = {'name': r_s[0]['legs'][0]['origin']['name'], 'lines': []}
            for l in r_s:
                l = l['legs'][0]
                if l['mode'].lower() == 'train':  # only count trains
                    departure_time = time.strptime(l['departure'], "%Y-%m-%dT%H:%M:%S%z")
                    countdown = round((time.mktime(departure_time) + 3600 - time.mktime(time.localtime())) / 60)
                    line = {
                        'departures': [max(0, countdown)],
                        'direction': l['destination']['name'],
                        'name': l['line']['product']['shortName'].rjust(3),
                        'trafficJam': False,  # no data from api
                        'barrierFree': False  # no data from api
                    }
                    station['lines'].append(line)

            oebb_data.append(station)

        renamed_stations = self._replace_station_and_direction_names(oebb_data)
        premerged_stations = self._merge_stations_by_name(renamed_stations)
        oebb_data = self._merge_lines_by_direction(premerged_stations)

        logger.debug("retrieved data: %s" % oebb_data)
        self.data = oebb_data
