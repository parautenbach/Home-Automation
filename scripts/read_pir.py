#!/usr/bin/python

# https://thepihut.com/blogs/raspberry-pi-tutorials/raspberry-pi-gpio-sensing-motion-detection

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

#PIR_PIN = 1  # board pin 12
PIR_PIN = 4  # 16
#PIR_PIN = 5  # 18
#PIR_PIN = 18

GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

time.sleep(2)

try:
	while True:
        	if GPIO.input(PIR_PIN):
                	print("Motion Detected!")
                else:
			print("No motion detected")
		time.sleep(2)
except KeyboardInterrupt:
        GPIO.cleanup()
