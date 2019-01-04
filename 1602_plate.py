#!/usr/bin/python
import time
import Adafruit_CharLCD as LCD
import subprocess
import datetime
from influxdb import InfluxDBClient  # for collecting data
import socket  # for hostname
import configparser # for parsing config.ini file
import sys

# Initialize the LCD using the pins
lcd = LCD.Adafruit_CharLCDPlate()
# Allow user to set session and runno via args otherwise auto-generate
if len(sys.argv) is 2:
        configpath = sys.argv[1]
else:
    print("ParameterError: You must define the path to the config.ini!")
    sys.exit()

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

hostname = socket.gethostname()

# Create the InfluxDB object
client = InfluxDBClient(host, port, user, password, dbname)
query = 'select last(*) from '+session
result = list()

def run_query():
    global result 
    result = list(client.query(query).get_points())
lcd.clear()
lcd.message(datetime.datetime.now().strftime('%b %d  %H:%M:%S\n'))
run_query()
#cmd = "ip -o addr | grep -v inet6 | awk '!/^[0-9]*: ?lo|link\/ether/ {print $2" "$4}'"
cmd = "ip -o addr | grep -v inet6 | awk '!/^[0-9]*: ?lo|link\/ether/ {print $4}'"


def run_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.communicate()[0]
    return output


ipaddr = run_cmd(cmd)
# Make list of button value, text, and backlight color.
buttons = ( (LCD.UP, 'IAQ: '+str(result[0]['last_iaq'])+'%', (1,1,1)),
            (LCD.LEFT,   'Temp: '+str(int(result[0]['last_temp']))+" C" , (1,0,0)),
            (LCD.SELECT,     'IP: '+ipaddr    , (0,0,1)),
            (LCD.DOWN,   'Humidity: '+str(int(result[0]['last_humi']))+'%', (0,1,0)),
            (LCD.RIGHT,  'Pressure: '+str(result[0]['last_press']) , (1,0,1)) )
while True:
    # Loop through each button and check if it is pressed.
    for button in buttons:
        if lcd.is_pressed(button[0]):
            # Button is pressed, change the message and backlight.
            lcd.clear()
            run_query()
            lcd.message(datetime.datetime.now().strftime('%b %d  %H:%M:%S\n'))
            lcd.message(button[1])
            lcd.set_color(button[2][0], button[2][1], button[2][2])
