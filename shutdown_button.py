#!/usr/bin/python3

import RPi.GPIO as GPIO
import os

GPIO_PIN=21

def my_callback(channel):
    os.system("sudo shutdown -h now")

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(GPIO_PIN, GPIO.RISING, callback=my_callback)
    input()

finally:
    GPIO.cleanup()
