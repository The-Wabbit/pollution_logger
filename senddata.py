#!/usr/bin/python3
import time  # for time and delay
import sys  # for arguments
import datetime  # for time and delay
from influxdb import InfluxDBClient  # for collecting data
import socket  # for hostname
import configparser # for parsing config.ini file
import adafruit_bme680
import board
import busio
import sds011

def get_raspid():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
    return cpuserial



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
    enable_gas = sensor.getboolean('enable_gas')
    session = sensor.get('session')
    location = sensor.get('location')
    temp_offset = float(sensor['temp_offset'])
    interval = int(sensor['interval'])
    burn_in_time = float(sensor['burn_in_time'])
    dust_port = sensor.get('serial_port')
    dust_baud = sensor.get('serial_baud')

except TypeError:
    print("TypeError parsing config.ini file. Check boolean datatypes!")
    sys.exit()
except KeyError:
    print("KeyError parsing config.ini file. Check file and its structure!")
    sys.exit()
except ValueError:
    print("ValueError parsing config.ini file. Check number datatypes!")
    sys.exit()

# Initialise I2C bus.
i2c = busio.I2C(board.SCL, board.SDA)
# Initialize the sensor
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

raspid = get_raspid()

now = datetime.datetime.now()
runNo = now.strftime("%Y%m%d%H%M")
hostname = socket.gethostname()

# Initialize the dust sensor
dust = sds011.SDS011(dust_port, use_query_mode=True)


print("Session: ", session)
print("runNo: ", runNo)
print("raspid: ", raspid)
print("hostname: ", hostname)
print("location: ", location)

# Create the InfluxDB object
client = InfluxDBClient(host, port, user, password, dbname)


# BME680 configuration
# Set sensor configs
#sensor.set_humidity_oversample(bme680.OS_2X)
#sensor.set_pressure_oversample(bme680.OS_4X)
#sensor.set_temperature_oversample(bme680.OS_8X)
#sensor.set_filter(bme680.FILTER_SIZE_3)
#sensor.set_temp_offset(temp_offset)

#if enable_gas:
#    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
#    sensor.set_gas_heater_temperature(320)
#    sensor.set_gas_heater_duration(150)
#    sensor.select_gas_heater_profile(0)
#else:
#    sensor.set_gas_status(bme680.DISABLE_GAS_MEAS)

# start_time and curr_time ensure that the
# burn_in_time (in seconds) is kept track of.
start_time = time.time()
curr_time = time.time()
burn_in_data = []
dust_values = []
# Run until keyboard out
try:
    # Collect gas resistance burn-in values, then use the average
    # of the last 50 values to set the upper limit for calculating
    # gas_baseline.
    if enable_gas:
        print("Collecting gas resistance burn-in data\n")
        while curr_time - start_time < burn_in_time:
            curr_time = time.time()
#            if sensor.data.heat_stable:
            gas = sensor.gas
            burn_in_data.append(gas)
            print("Gas: {0} Ohms".format(gas))
            time.sleep(1)

        gas_baseline = int(sum(burn_in_data[-50:]) / 50.0)

        # Set the humidity baseline to 40%, an optimal indoor humidity.
        hum_baseline = 40.0

        # This sets the balance between humidity and gas reading in the
        # calculation of air_quality_score (25:75, humidity:gas)
        hum_weighting = 0.25

        print("Gas baseline: {0} Ohms, humidity baseline: {1:.2f} %RH\n".format(gas_baseline, hum_baseline))

    # Sensor read loop
    while True:
        hum = sensor.humidity
        temp = sensor.temperature - temp_offset
        press = sensor.pressure
        dust_values=dust.query()
        iso = time.ctime()
        if enable_gas:
            hum_offset = hum - hum_baseline
            gas = int(sensor.gas)
            gas_offset = gas_baseline - gas

            # Calculate hum_score as the distance from the hum_baseline.
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)

            else:
                hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)

            # Calculate gas_score as the distance from the gas_baseline.
            if gas_offset > 0:
                gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))

            else:
                gas_score = 100 - (hum_weighting * 100)

            # Calculate air_quality_score.
            air_quality_score = hum_score + gas_score
            # Round to full
            air_quality_score = round(air_quality_score, 0)

            json_body = [
                {
                    "measurement": session,
                    "tags": {
                        "run": runNo,
                        "raspid": raspid,
                        "hostname": hostname,
                        "location": location
                    },
                    "time": iso,
                    "fields": {
                        "temp": temp,
                        "press": press,
                        "humi": hum,
                        "gas": gas,
                        "iaq": air_quality_score,
                        "gasbaseline": gas_baseline,
                        "humbaseline": hum_baseline,
                        "PM25": dust_values[0],
                        "PM10": dust_values[1]
                    }
                }
            ]

        else:
            json_body = [
                {
                    "measurement": session,
                    "tags": {
                        "run": runNo,
                        "raspid": raspid,
                        "hostname": hostname,
                        "location": location
                    },
                    "time": iso,
                    "fields": {
                        "temp": temp,
                        "press": press,
                        "humi": hum,
                    }
                }
            ]

        print(json_body)

        # Write JSON to InfluxDB
        res = client.write_points(json_body,time_precision='s')
        print(res)
        # Wait for next sample
        time.sleep(interval)

except KeyboardInterrupt:
    pass
