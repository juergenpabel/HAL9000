#!/usr/bin/python3

import os
import sys
import time

from uwsgi import accepting
from paho.mqtt import client as mqtt_client

from devices.rfidreader import HAL9000_RFIDReader
from devices.rotaries import HAL9000_Rotaries
from devices.buttons import HAL9000_Buttons


mqtt = mqtt_client.Client('hal9000-enclosure-peripherals')
mqtt.connect("127.0.0.1", 1883)
mqtt.loop_start()

devices = dict()
devices['rfidreader'] = HAL9000_RFIDReader()
devices['rotaries'] = HAL9000_Rotaries()
devices['buttons'] = HAL9000_Buttons()

accepting()

for name, device in devices.items():
	device.configure()
while True:
	for name, device in devices.items():
		device.do_loop()
	time.sleep(0.001)
