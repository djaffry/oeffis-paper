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


def render(display_data, weather_data):
    conf = get_config()

    # Setup Image and Draw
    image_black = Image.new('L', DISPLAY_SIZE, 255)  # 255: clear the frame
    draw_black = ImageDraw.Draw(image_black)
    draw_black.fontmode = "L"  # less antialias of fonts

    image_red = Image.new('L', DISPLAY_SIZE, 255)  # 255: clear the frame
    draw_red = ImageDraw.Draw(image_red)
    draw_red.fontmode = "L"  # less antialias of fonts

    # Header: Title and Server Time
    draw_red.rectangle(((0, 0), (DISPLAY_WIDTH, 42)), fill=0)
    draw_red.text((10, 10), conf['display']['title'], font=TITLE_FONT, fill=255)

    minute_val = time.strftime("%M", display_data['lastUpdate'])
    hour_val = time.strftime("%H", display_data['lastUpdate'])
    draw_red.text((305, 10), hour_val, font=TITLE_FONT, fill=255)
    draw_red.text((336, 10), ":", font=TITLE_FONT, fill=255)
    draw_red.text((345, 10), minute_val.zfill(2), font=TITLE_FONT, fill=255)

    # Main: Public Transport Data
    y_offset = 55
    for station in sorted(display_data['stations'], key=lambda s: s['name']):
        if 'citybikewien' in station:
            draw_red.text((10, y_offset), _format_addr(station['name'], 23), font=TITLE_FONT, fill=0)
            draw_red.bitmap((307, 4 + y_offset),
                            Image.open(CITYBIKEWIEN_ASSETS_DIR + 'citybikewien.png').resize((25, 20), Image.ANTIALIAS),
                            fill=0)
            draw_red.text((345, 7 + y_offset), station['citybikewien']['bikes'].zfill(2), font=MONO_FONT, fill=0)
        else:
            draw_red.text((10, y_offset), _format_addr(station['name'], 26), font=TITLE_FONT, fill=0)

        if 'lines' in station:
            for line in sorted(station['lines'], key=lambda l: l['name'] + l['direction']):
                draw_black.text((10, 35 + y_offset), line['name'], font=MONO_FONT, fill=0)

                line['direction'] = _format_addr(line['direction'], 17)
                draw_black.text((60, 35 + y_offset), line['direction'], font=MONO_FONT, fill=0)

                if line['trafficJam']:
                    draw_red.bitmap((270, 38 + y_offset),
                                    Image.open(IONICONS_ASSETS_DIR + "ionicons_alert_md.png").resize((18, 18),
                                                                                                     Image.ANTIALIAS),
                                    fill=0)

                if len(line['departures']) > 0:
                    if 'walkingTime' in station and station['walkingTime'] + conf['stations']['avgWaitingTime'] >= \
                            line['departures'][0] >= station['walkingTime']:
                        draw_red.text((305, 35 + y_offset), _display_countdown(line['departures'][0]), font=MONO_FONT,
                                      fill=0)
                    else:
                        draw_black.text((305, 35 + y_offset), _display_countdown(line['departures'][0]), font=MONO_FONT,
                                        fill=0)
                    if len(line['departures']) > 1:
                        if 'walkingTime' in station and station['walkingTime'] + conf['stations']['avgWaitingTime'] >= \
                                line['departures'][1] >= station['walkingTime']:
                            draw_red.text((345, 35 + y_offset), _display_countdown(line['departures'][1]),
                                          font=MONO_FONT,
                                          fill=0)
                        else:
                            draw_black.text((345, 35 + y_offset), _display_countdown(line['departures'][1]),
                                            font=MONO_FONT,
                                            fill=0)
                y_offset = y_offset + 25
        y_offset = y_offset + 45

    # Footer: Weather data
    if bool(weather_data):
        draw_red.rectangle(((0, 564), (DISPLAY_WIDTH, DISPLAY_HEIGHT)), fill=0)
        fst_row_height = 568
        snd_row_height = 598
        weather_cols = 2
        x_offset = 0
        for i in range(0, weather_cols):
            if not (int(DISPLAY_WIDTH / weather_cols) + x_offset + 1 >= DISPLAY_WIDTH):
                draw_red.rectangle(((int(DISPLAY_WIDTH / weather_cols) + x_offset, 564 + 3),
                                    (int(DISPLAY_WIDTH / weather_cols) + 1 + x_offset, DISPLAY_HEIGHT - 3)), fill=255)
            draw_red.text((10 + x_offset, fst_row_height), time.strftime("%H:%M", weather_data['forecast'][i]['time']['from']),
                          font=MONO_FONT, fill=255)
            draw_red.text((int(DISPLAY_WIDTH / weather_cols) - 74 + x_offset, fst_row_height),
                          weather_data['forecast'][i]['celsius'].rjust(3) + '°C', font=MONO_FONT, fill=255)

            weather_id = str(weather_data['forecast'][i]['symbol']['id']).zfill(2)
            is_night = weather_data['sun']['rise'] > time.localtime() > weather_data['sun'][
                'set']  # check if current time is between sunset and sunrise
            icon = YR_ASSETS_DIR + weather_id + (is_night if '' else 'n') + '.png'  # get specific icon from assets folder
            try:
                img = Image.open(icon)
            except FileNotFoundError:  # if there is no night icon for the weather type, then use day time variant instead
                try:
                    img = Image.open(YR_ASSETS_DIR + weather_id + '.png')
                except FileNotFoundError as err:
                    logger.error(
                        "No YR icon named %s found! Have you run the setup script?" % (YR_ASSETS_DIR + weather_id + '.png'))
                    raise err
            img = img.convert("RGBA").resize((35, 35), Image.ANTIALIAS)
            draw_red.bitmap((10 + x_offset, snd_row_height - 2), img, fill=255)
            draw_red.text((int(DISPLAY_WIDTH / weather_cols) - 99 + x_offset, snd_row_height),
                          str(weather_data['forecast'][i]['wind']['mps']).rjust(3) + "km/h", font=MONO_FONT, fill=255)

            x_offset = x_offset + int(DISPLAY_WIDTH / weather_cols)

    return image_black.rotate(90, expand=True), image_red.rotate(90, expand=True)


def render_exception(err, err_type, msg_list=None):
    if msg_list is None:
        msg_list = []
    import textwrap

    image_black = Image.new('L', DISPLAY_SIZE, 255)  # 255: clear the frame
    draw_black = ImageDraw.Draw(image_black)
    image_red = Image.new('L', DISPLAY_SIZE, 255)  # 255: clear the frame
    draw_red = ImageDraw.Draw(image_red)

    y_offset = 20
    draw_red.text((10, y_offset), err_type, font=TITLE_FONT, fill=0)

    lines = textwrap.wrap(err, width=36)

    y_offset = y_offset + 10
    for line in lines:
        y_offset = y_offset + 25
        draw_black.text((10, y_offset), line, font=MONO_FONT, fill=0)

    if msg_list is not []:
        small_mono_font = ImageFont.truetype('fonts/UbuntuMono-R.ttf', 18)
        flattened = lambda li: [i for sublist in li for i in sublist]

        y_offset = y_offset + 5
        formatted_lines = flattened([textwrap.wrap(str(msg), width=36) for msg in msg_list])
        for line in formatted_lines:
            y_offset = y_offset + 25
            draw_black.text((10, y_offset), line, font=small_mono_font, fill=0)

    return image_black, image_red
