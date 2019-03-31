from .bpm_render import render, render_exception
from utils import get_config
from utils import get_logger
import time
# from lib.waveshare.epd7in5b import EPD

logger = get_logger(__name__)


class UIDriver:
    def __init__(self):
        self.driver = None
        # self.driver = EPD()
        if self.driver is not None:
            self.driver.init()

    def display(self, traffic_data, weather_data):
        """
        If drivers are loaded, correct traffic_data times and display on e-paper
        else show it on desktop
        :param traffic_data: merged traffic_data with walk times
        :param weather_data: weather_data from api
        """
        if self.driver is not None:
            traffic_data = self._adjust_to_render_offset(traffic_data)
        image_black, image_red = render(traffic_data, weather_data)
        self._show(image_black, image_red)

    def display_exception(self, err, msg_list=None):
        if msg_list is None:
            msg_list = []

        if self.driver is not None:
            self.driver.Clear(0xFF)
        image_black, image_red = render_exception(err, msg_list)
        self._show(image_black, image_red)

    def _show(self, image_black, image_red):
        if self.driver is not None:
            # show image on e-paper display
            self.driver.display(self.driver.getbuffer(image_black), self.driver.getbuffer(image_red))
        else:
            # show image on monitor
            image_black.show()
            image_red.show()

    @staticmethod
    def _adjust_to_render_offset(transport_data):
        """
        Unfortunately the waveshare display takes about 60 seconds to display the information.
        Therefore the displayed time can be corrected by adding `renderOffset` to the server time minutes and
        subtracting `renderOffset` from the countdown time

        Input:
        Uses data from `config.json` with the following keys:
        display (json):                       display json with the following keys:
            renderOffset (number, optional):            offset in minutes used to add to displayed server time and subtract countdown

        :param transport_data
        :return: time adjusted transport_data
        """

        conf = get_config()
        if 'renderOffset' in conf['display']:
            corrected_seconds = time.mktime(transport_data['lastUpdate']) + conf['display']['renderOffset'] * 60
            transport_data['lastUpdate'] = time.localtime(corrected_seconds)

            offset_data = []
            for s in transport_data['stations']:
                for l in s['lines']:
                    # subtract `renderOffset` from countdown time
                    l['departures'] = [d - conf['display']['renderOffset']
                                       for d in l['departures'] if d - conf['display']['renderOffset'] >= 0]
                    if not l['departures']:
                        s['lines'].remove(l)  # removing lines with no departure time
                if s['lines']:
                    offset_data.append(s)  # removing stations with no lines
            return {'stations': offset_data, 'lastUpdate': transport_data['lastUpdate']}
        else:
            return transport_data
