#!/usr/bin/python

# https://thepihut.com/blogs/raspberry-pi-tutorials/raspberry-pi-gpio-sensing-motion-detection

#!/usr/bin/env python

from time import sleep  # Allows us to call the sleep function to slow down our loop
import RPi.GPIO as GPIO # Allows us to call our GPIO pins and names it just GPIO
 
GPIO.setmode(GPIO.BCM)  # Set's GPIO pins to BCM GPIO numbering
INPUT_PIN = 23  # 18           # Sets our input pin, in this example I'm connecting our button to pin 4. Pin 0 is the SDA pin so I avoid using it for sensors/buttons
GPIO.setup(INPUT_PIN, GPIO.IN)  # Set our input pin to be an input

OUTPUT_PIN = 24
GPIO.setup(OUTPUT_PIN, GPIO.OUT)

# Create a function to run when the input is high
def input(channel):
    print('yes')
    GPIO.output(OUTPUT_PIN, GPIO.HIGH)

GPIO.add_event_detect(INPUT_PIN, GPIO.RISING, callback=input, bouncetime=1000) # Wait for the input to go low, run the function when it does

# Start a loop that never ends
try:
    while True:
        print('no')
        GPIO.output(OUTPUT_PIN, GPIO.LOW)
        sleep(2)           # Sleep for a full second before restarting our loop
except KeyboardInterrupt:
        GPIO.cleanup()
