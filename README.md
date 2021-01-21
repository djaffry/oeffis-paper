
# Öffis Paper

Raspberry Pi based real time Vienna public transport monitor using a triple color E-ink display  
Get public transport information instantly, like being at a real station!

Öffis &rarr; austrian slang for public transport

<p align="center">
  <img height=500 src="https://github.com/djaffry/oeffis-paper/blob/master/pics/standing.jpg" alt="Öffis Paper Standing">
</p>

more pictures in the [pics](pics) folder

> :warning: Unfortunately, my 7.5inch E-Ink display broke. So I cannot update this project anymore. Feel free to fork this project and tinker by yourself!


## Features
- Displays ÖBB and Wiener Linien public transport times, Citybike Wien station capacities and weather at a glance
- Intuitive UI, see time, stations with their lines and weather on a 7.5 inch E-ink screen
- Config file for easier configuring without changing code
- Citybike Wien API for CitybikeWien station data, written in Python3
- [juliuste's oebb](https://github.com/juliuste/oebb/) for getting the ETA of the upcoming ÖBB trains as a countdown in minutes
- Wiener Linien API for getting the ETA of upcoming busses, trams or metros as a countdown in minutes, written in Python3
- yr.no API for weather data, written in Python3

## Hardware used 
- 640x384, 7.5inch E-Ink display HAT Model B (Red, Black, White) for Raspberry Pi &rarr; [waveshare.com](https://www.waveshare.com/7.5inch-e-paper-hat-b.htm), [amazon.com](https://www.amazon.com/7-5inch-HAT-Three-color-consumption-Resolution/dp/B075YP81JR/), [amazon.at](https://www.amazon.de/Tri-Color-Electronic-Compatible-Raspberry-Interface/dp/B076BRRSD3/)
- Raspberry Pi Zero W with soldered headers or any Raspberry Pi 2 and up (tested with zero W and PI 3B+) &rarr; [Raspberry Pi Website](https://www.raspberrypi.org/products/), [conrad.at](https://www.conrad.at/de/Search.html?search=raspberry%20pi), or search at [amazon.at](https://www.amazon.de/ref=rd_www_amazon_at/?site-redirect=at).
- Class 10 Micro SD Card with at least 8GB (16GB recommended) for the Raspberry Pi.
- A typical 5V micro USB phone charger to charge the Raspberry Pi

<p align="center">
  <img height=500 src="https://github.com/djaffry/oeffis-paper/blob/master/pics/wiring.jpg" alt="Öffis Paper Wiring">
</p>

## Getting Started

### 1. Hardware Setup
* Setup the Raspberry Pi. You can find a manual on how to and official images for `Raspbian` (recommended) at the [Raspberry Pi Download Page](https://www.raspberrypi.org/downloads/). 
    * If you wish to not use `Raspbian`, you have to do parts of the `oeffis-paper` setup later by yourself. These parts will be prompted to you. 
    * If you choose the Raspbian image, the `scripts/setup.sh` script will later install all required dependencies, fonts and assets for you.
* Assemble the Waveshare E-Ink Display and HAT as written in the waveshare manual and connect it to the Raspberry Pi. Since the HAT can be plugged directly onto the GPIO headers, this process should not be to difficult. Don't forget to activate the Pi's [SPI](https://www.raspberrypi.org/documentation/configuration/raspi-config.md)!
* Optionally print some case for the `oeffis-paper` hardware or use a picture frame. This is what I used: [IKEA Ribba](https://www.ikea.com/at/de/p/ribba-rahmen-weiss-70378414/)

### 2. Clone the repository:
Install `git` (`sudo apt install git`) and run the following code:
```bash
git clone https://github.com/djaffry/oeffis-paper.git ~/oeffis-paper
```

### 3. Configure config.json

An example [config.json](./config.json) can be found in the root directory.
Descriptions to the different key-value pairs can be found in the respective classes or here:

* `display` (json) - display relevant configurations
    * `renderOffset` (int, optional) - corrects displayed time and minutes until arrival by this offset in minutes, counters display hysteresis
    * `updateInterval` (int) - the display will try to update every `updateInterval` seconds. due to delay, sometimes this is not possible 
    * `title` (string) - title displayed in the upper left corner of display

* `stations` (json) - station relevant configurations
    * `avgWaitingTime` (int) - time which is acceptable to wait for transport at a station
    * `walkingTime` (array[json]) - how long it takes to walk to a station
        * `station` (string) - station name to walk to
        * `time` (int) - how long it takes to walk to that station in minutes

* `api` (json) - api relevant configurations
    * `citybikewien` (json, optional) - citybikewien configurations 
        * `updateInterval`(int) - minimum of how long until the next API call should be made in seconds
        * `stations` (array[json]) - jsons with station ids and values
            * `id` (int) - id of station ([see Citybike Wien Data](#citybike-wien-data-(optional)))
            * `rename` (str, optional) - use this value instead of the api's station name
            
    * `oebb` (json, optional) - ÖBB configurations
        * `updateInterval`(int) - minimum of how long until the next API call should be made in seconds
        * `connections` (array[json]) - jsons of connections
            * `from` (string) - departure station oebb id ([see ÖBB Data](#öbb-data))
            * `to` (string) - destination station oebb id ([see ÖBB Data](#öbb-data))
        * `rename` (array[json], optional) - to rename stations 
            * `old` (string) - old name to be replaced, so it can be merged by name with other stations
            * `new` (string) - new name to be renamed into
    
    * `wrlinien` (json, optional) - Wiener Linien configurations
        * `updateInterval` (int) - minimum of how long until the next API call should be made in seconds
        * `key` (string) - Wiener Linien API key ([see Wiener Linien Data](#wiener-linien-data))
        * `rbls` (array[int]) - Array of rbls (Wiener Linien station ids, see below)

    * `yrno` (json, optional) - yr.no configurations
        * `updateInterval` (int) - minimum of how long until the next API call should be made in seconds
        * `city` (string) - name of the city ([see YR.NO Data](#yr.no-data))
        * `province` (string) - name of the province ([see YR.NO Data](#yr.no-data))
        * `country` (string) - name of the country ([see YR.NO Data](#yr.no-data))
        

#### Citybike Wien Data (optional)
The Citybike Wien station names and id's can be extracted from [CitybikeWien Liste](http://www.cbw.at/liste.php).
The `id` can be found left to the station's name. Example Station Rathausplatz: `110 RATHAUSPLATZ` therefore `"id": 110`.

#### ÖBB Data
To get the necessary ÖBB Station IDs use [djaffry/oebb-stations](https://github.com/djaffry/oebb-stations).

#### Wiener Linien Data
**Important**: You will need a _Wiener Linien API Key_ to access the Wiener Linien API. They are free and you can apply for one using [this form](https://go.gv.at/l9ogdechtzeitdatenwienerlinienkeyanforderung).

To get the RBL to your station, you have to look them up in the `csv` files at [data.gv.at](https://www.data.gv.at/katalog/dataset/stadt-wien_wienerlinienechtzeitdaten).
By looking up your _HALTESTELLEN_ID_ in `csv-haltestellen` and the _LINIEN_id_ in `csv-linien` you can defer the right row for the _RBL_NUMMER_ (`rbl`) in `csv-steige`.

Or have a look here: https://till.mabe.at/rbl/

#### YR.NO Data
To find the right city, province and country name, just search for your location at [yr.no](https://www.yr.no/), 
go to the respective site of the city. Then use the parts after `place` in the URL for the values as `country/province/city`.

Example: Bischofshofen, AT https://www.yr.no/place/Austria/Salzburg/Bischofshofen/
Results in: 
```json
{
  ...
  "country": "Austria",
  "province": "Salzburg",
  "city": "Bischofshofen"
}
```


### 4. Install dependencies
A `setup.sh` script can be found in the [scripts directory](scripts). Running it will resolve all dependencies.
`setup.sh` will also fix the waveshare libraries imports and some arithmetic errors in the waveshare library using patches which can be found in the [patches subdirectory](scripts/patches).
You can run `./setup.sh` anytime again to update dependencies, fonts and assets.
```bash
cd ~/oeffis-paper/scripts
./setup.sh
```

### 5. How to run and stop
Further two scripts can be found in [scripts](scripts):
* Use `./start.sh` to run in background. This process does not get killed when closing the `ssh` connection used to start the process.
* Use `./kill.sh` to kill the current background process.
