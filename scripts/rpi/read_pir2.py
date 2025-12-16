#!/usr/bin/python

# https://tutorials-raspberrypi.com/connect-and-control-raspberry-pi-motion-detector-pir/

import RPi.GPIO as GPIO
import time

#SENSOR_PIN = 1  # board pin 12
#SENSOR_PIN = 18
SENSOR_PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)

time.sleep(2)

def my_callback(channel):
    # Here, alternatively, an application / command etc. can be started.
    print("Movement detected!")

try:
    GPIO.add_event_detect(SENSOR_PIN , GPIO.RISING, callback=my_callback)  #, bouncetime=1000)
    while True:
        print("Tick")
        time.sleep(5)
except KeyboardInterrupt:
    print("Quiting")
finally:
    GPIO.cleanup()
