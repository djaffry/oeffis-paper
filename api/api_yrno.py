import xml.etree.ElementTree as ET
import requests
from requests import RequestException, HTTPError

from utils import get_config, get_logger
import time

logger = get_logger(__name__)
time_format_str = '%Y-%m-%dT%H:%M:%S'


class YRNOApi:
    """
    Get weather updates from yr.no API and parse to a `dict`, then cache the `dict` as `self.data`

    Input:
    Uses data from `config.json` with the following keys:
        weather (json):                     weather json with the following keys:
            updateInterval (number):        minimum of how long until the next API call should be made in seconds
            city (str):                     name of city
            province (str):                 name of province
            country (str):                  name of country

    Output:
    self.data: `None` or `dict` with the following keys:
        country (str):                      name of country
        city (str):                         name of city
        sun (dict):                         sunset and sunrise data
            set (time.struct_time):         time of sunset
            rise (time.struct_time):        time of sunrise
        forecast (array[dict]):             array of forecasts
            precipitation (int):            precipitation in mm
            celsius (int):                  degrees celsius
            time (dict):                    time range of the forecast
                from (time.struct_time):    lower bound of valid time range
                to (time.struct_time):      upper bound of valid time range
            symbol (dict):                  icon symbol and name of the current weather
                id (number):                yr.no id of the symbol
                description (str):          current weather description
            wind (dict):                    wind data
                direction (str):            wind direction abbreviated to 3 `char`s
                description (str):          wind type description
                mps (float):                wind speed in meters per second
            credit (dict):                  yr.no credits
                url (str):                  url to yr.no website of requested location
                text (str):                 yr.no credits text
        lastUpdate (time.struct_time):  server timestamp of update

    Example self.data:
    {
        'country': 'Austria',
        'city': 'Vienna',
        'sun': {
            'set': time.struct_time(...),
            'rise': time.struct_time(...)
        },
        'forecast': [
            {
                'precipitation': '0',
                'celsius': '8',
                'time': {
                    'to': time.struct_time(...),
                    'from': time.struct_time(...)
                },
                'symbol': {
                    'id': '4',
                    'description': 'Cloudy'
                },
                'wind': {
                    'direction': 'WNW',
                    'description': 'Gentle breeze',
                    'mps': '3.7'
                }
            }, {
                'precipitation': '1.9',
                'celsius': '8',
                'time': {
                    'to': time.struct_time(...),
                    'from': time.struct_time(...)
                },
                'symbol': {
                    'id': '9',
                    'description': 'Rain'
                },
                'wind': {
                    'direction': 'WNW',
                    'description': 'Moderate breeze',
                    'mps': '6.3'
                }
            }
        ],
        'credit': {
            'url': 'http: //www.yr.no/place/Austria/Vienna/Vienna/',
            'text': 'Weather forecast from Yr, delivered by the Norwegian Meteorological Institute and the NRK'
        },
        'lastUpdate': time.struct_time(...)
    }
    """

    def __init__(self):
        self.exc_info = None  # exception for main thread
        self.data = None  # fetched data
        self.nextUpdate = 0  # time when next update can be done in seconds since the Epoch

    def reset(self):
        self.__init__()

    def update(self):
        """
        Updates self.data iff an update is needed, else does nothing
        """
        try:
            if self.nextUpdate <= time.time():
                self._get_data()
                conf = get_config()
                self.nextUpdate = time.time() + conf['api']['yrno']['updateInterval']
        except Exception as err:
            import sys
            self.exc_info = sys.exc_info()

    def _get_data(self):
        conf = get_config()
        try:
            res = requests.post('https://www.yr.no/place/%s/%s/%s/forecast.xml'
                                % (conf['api']['yrno']['country'], conf['api']['yrno']['province'], conf['api']['yrno']['city']))
        except RequestException or HTTPError:  # retry on error
            logger.error("Caught RequestException")
            res = requests.post('https://www.yr.no/place/%s/%s/%s/forecast.xml'
                                % (conf['api']['yrno']['country'], conf['api']['yrno']['province'], conf['api']['yrno']['city']))
        res.raise_for_status()
        root = ET.fromstring(res.text)

        # filter data and parse to weather dict
        legal_xml = root.find('credit').find('link')
        location_xml = root.find('location')
        sun_xml = root.find('sun')
        weather_data = {
            'credit': {
                "text": legal_xml.get('text'),
                "url": legal_xml.get('url')
            },
            'city': location_xml.find('name').text,
            'country': location_xml.find('country').text,
            'lastUpdate': time.strptime(root.find('meta').find('lastupdate').text, time_format_str),
            'sun': {
                "rise": time.strptime(sun_xml.get('rise'), time_format_str),
                "set": time.strptime(sun_xml.get('set'), time_format_str)
            },
            "forecast": []
        }
        tabular_xml = root.find('forecast').find('tabular')
        for time_xml in tabular_xml.findall('time'):
            symbol_xml = time_xml.find('symbol')
            wind_xml = time_xml.find('windSpeed')
            weather_data['forecast'].append({
                'time': {
                    "from": time.strptime(time_xml.get('from'), time_format_str),
                    "to": time.strptime(time_xml.get('to'), time_format_str)
                },
                'symbol': {
                    "id": symbol_xml.get('number'),
                    "description": symbol_xml.get('name')
                },
                'precipitation': time_xml.find('precipitation').get('value'),
                'wind': {
                    "direction": time_xml.find('windDirection').get('code'),
                    "mps": wind_xml.get('mps'),
                    "description": wind_xml.get('name')
                },
                "celsius": time_xml.find('temperature').get('value')
            })

        logger.info("retrieved data: %s" % weather_data)
        self.data = weather_data
