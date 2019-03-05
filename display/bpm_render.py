from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import time
from utils import get_config, get_logger

logger = get_logger(__name__)

DISPLAY_HEIGHT = 640
DISPLAY_WIDTH = 384
DISPLAY_SIZE = (DISPLAY_WIDTH, DISPLAY_HEIGHT)

TITLE_FONT = ImageFont.truetype('fonts/Ubuntu-M.ttf', 24)
MONO_FONT = ImageFont.truetype('fonts/UbuntuMono-R.ttf', 22)
# ICON_FONT = ImageFont.truetype('fonts/DejaVuSansMono.ttf', 55)

CITYBIKEWIEN_ASSETS_DIR = 'assets/citybikewien/'
YR_ASSETS_DIR = 'assets/yr/'
IONICONS_ASSETS_DIR = 'assets/ionicons/'


def _display_countdown(num):
    if num == 0:
        return '**'
    else:
        return str(num).zfill(2)


def _format_name(name, length):
    if len(name) > length:
        return name[:(length - 2)] + '…'
    else:
        return name


def _format_addr(addr, length):
    # str.replace is sufficient for now, might cause with 'Tassenplatz' or similar in the future
    if addr.isupper():
        addr = addr.title()
    if len(addr) > length:
        addr = addr.replace('asse', '.') \
            .replace('traße', 'tr.') \
            .replace('latz', 'pl.')
    return _format_name(addr, length)


def render(display_data, weather):
    conf = get_config()

    # Setup Image and Draw
    image = Image.new('L', DISPLAY_SIZE, 255)  # 255: clear the frame
    draw = ImageDraw.Draw(image)
    draw.fontmode = "L"  # less antialias of fonts

    # Header: Title and Server Time
    draw.rectangle(((0, 0), (DISPLAY_WIDTH, 42)), fill=127)
    draw.text((10, 10), conf['display']['title'], font=TITLE_FONT, fill=255)

    minute_val = time.strftime("%M", display_data['lastUpdate'])
    hour_val = time.strftime("%H", display_data['lastUpdate'])
    draw.text((305, 10), hour_val, font=TITLE_FONT, fill=255)
    draw.text((336, 10), ":", font=TITLE_FONT, fill=255)
    draw.text((345, 10), minute_val.zfill(2), font=TITLE_FONT, fill=255)

    # Main: Public Transport Data
    y_offset = 55
    for station in sorted(display_data['stations'], key=lambda s: s['name']):
        if 'citybikewien' in station:
            draw.text((10, y_offset), _format_addr(station['name'], 23), font=TITLE_FONT, fill=127)
            draw.bitmap((307, 4 + y_offset), Image.open(CITYBIKEWIEN_ASSETS_DIR + 'citybikewien.png').resize((25, 20), Image.ANTIALIAS), fill=127)
            draw.text((345, 7 + y_offset), station['citybikewien']['bikes'].zfill(2), font=MONO_FONT, fill=127)
        else:
            draw.text((10, y_offset), _format_addr(station['name'], 26), font=TITLE_FONT, fill=127)

        if 'lines' in station:
            for line in sorted(station['lines'], key=lambda l: l['name'] + l['direction']):
                draw.text((10, 35 + y_offset), line['name'], font=MONO_FONT, fill=0)

                line['direction'] = _format_addr(line['direction'], 17)
                draw.text((60, 35 + y_offset), line['direction'], font=MONO_FONT, fill=0)

                if line['trafficJam']:
                    draw.bitmap((270, 38 + y_offset), Image.open(IONICONS_ASSETS_DIR + "ionicons_alert_md.png").resize((18, 18), Image.ANTIALIAS), fill=127)

                if len(line['departures']) > 0:
                    if 'walkingTime' in station and station['walkingTime'] + conf['stations']['avgWaitingTime'] >= \
                            line['departures'][0] >= station['walkingTime']:
                        draw.text((305, 35 + y_offset), _display_countdown(line['departures'][0]), font=MONO_FONT, fill=127)
                    else:
                        draw.text((305, 35 + y_offset), _display_countdown(line['departures'][0]), font=MONO_FONT, fill=0)
                    if len(line['departures']) > 1:
                        if 'walkingTime' in station and station['walkingTime'] + conf['stations']['avgWaitingTime'] >= \
                                line['departures'][1] >= station['walkingTime']:
                            draw.text((345, 35 + y_offset), _display_countdown(line['departures'][1]), font=MONO_FONT, fill=127)
                        else:
                            draw.text((345, 35 + y_offset), _display_countdown(line['departures'][1]), font=MONO_FONT, fill=0)
                y_offset = y_offset + 25
        y_offset = y_offset + 45

    # Footer: Weather data
    draw.rectangle(((0, 564), (DISPLAY_WIDTH, DISPLAY_HEIGHT)), fill=127)
    fst_row_height = 568
    snd_row_height = 598
    weather_cols = 2
    x_offset = 0
    for i in range(0, weather_cols):
        if not (int(DISPLAY_WIDTH / weather_cols) + x_offset + 1 >= DISPLAY_WIDTH):
            draw.rectangle(((int(DISPLAY_WIDTH / weather_cols) + x_offset, 564 + 3), (int(DISPLAY_WIDTH / weather_cols) + 1 + x_offset, DISPLAY_HEIGHT - 3)), fill=255)
        draw.text((10 + x_offset, fst_row_height), time.strftime("%H:%M", weather['forecast'][i]['time']['from']), font=MONO_FONT, fill=255)
        draw.text((int(DISPLAY_WIDTH / weather_cols) - 74 + x_offset, fst_row_height), weather['forecast'][i]['celsius'].rjust(3) + '°C', font=MONO_FONT, fill=255)

        weather_id = str(weather['forecast'][i]['symbol']['id']).zfill(2)
        is_night = weather['sun']['rise'] > time.localtime() > weather['sun']['set']  # check if current time is between sunset and sunrise
        icon = YR_ASSETS_DIR + weather_id + (is_night if '' else 'n') + '.png'  # get specific icon from assets folder
        try:
            img = Image.open(icon)
        except FileNotFoundError:  # if there is no night icon for the weather type, then use day time variant instead
            try:
                img = Image.open(YR_ASSETS_DIR + weather_id + '.png')
            except FileNotFoundError as err:
                logger.error("No YR icon named %s found! Have you run the setup script?" % (YR_ASSETS_DIR + weather_id + '.png'))
                raise err
        img = img.convert("RGBA").resize((35, 35), Image.ANTIALIAS)
        draw.bitmap((10 + x_offset, snd_row_height - 2), img, fill=255)
        draw.text((int(DISPLAY_WIDTH / weather_cols) - 99 + x_offset, snd_row_height), str(weather['forecast'][i]['wind']['mps']).rjust(3) + "km/h", font=MONO_FONT, fill=255)

        x_offset = x_offset + int(DISPLAY_WIDTH / weather_cols)

    return image
