#!/usr/bin/python3
import time
import sys
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from influxdb import InfluxDBClient  # for collecting data
import configparser # for parsing config.ini file

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

# Allow user to set session and runno via args otherwise auto-generate
if len(sys.argv) is 2:
        configpath = sys.argv[1]
else:
        configpath = './config.ini'
# Parsing the config parameters from config.ini
config = configparser.ConfigParser()
try:
    config.read(configpath)
    influxserver = config['influxserver']
    host = influxserver.get('host')
    port = influxserver.get('port')
    user = influxserver.get('user')
    password = influxserver.get('password')
    dbname = influxserver.get('dbname')
    sensor = config['sensor']
    session = sensor.get('session')
except TypeError:
    print("TypeError parsing config.ini file. Check boolean datatypes!")
    sys.exit()
except KeyError:
    print("KeyError parsing config.ini file. Check file and its structure!")
    sys.exit()
except ValueError:
    print("ValueError parsing config.ini file. Check number datatypes!")
    sys.exit()

# Create the InfluxDB object
client = InfluxDBClient(host, port, user, password, dbname)
query = 'select last(*) from '+session
result = list()


# Raspberry Pi pin configuration:
RST = 24
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# Initialize 128x64 display with hardware SPI:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))
disp.begin()
# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

#Get the latest points from influxdb
def run_query():
    global result 
    result = list(client.query(query).get_points())


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    run_query()
    IAQ = result[0]['last_iaq']
    TEMP = result[0]['last_temp']
    PRESS = result[0]['last_press']
    HUMI = result[0]['last_humi']
    # Write two lines of text.

    draw.text((x, top),       "IP: " + str(IP),  font=font, fill=255)
    draw.text((x, top+8),     str(CPU), font=font, fill=255)
    draw.text((x, top+16),    str(MemUsage),  font=font, fill=255)
    draw.text((x, top+24),    str(Disk),  font=font, fill=255)
    draw.text((x, top+32),    "Temp: "+str(round(TEMP,2))+"C ", font=font, fill=255)
    draw.text((x, top+40),    "IAQ: "+str(int(IAQ))+"%", font=font, fill=255)
    draw.text((x, top+48),    "Humi: "+str(int(HUMI))+"%" , font=font, fill=255)
    draw.text((x, top+56),    "Press: "+str(int(PRESS)), font=font, fill=255)
    # Display image.
    disp.image(image)
    disp.display()
    time.sleep(.1)
