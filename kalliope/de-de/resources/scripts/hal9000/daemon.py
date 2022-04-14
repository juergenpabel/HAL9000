#!/usr/bin/python3

import os
import sys
import time
from hal9000 import HAL9000

from paho.mqtt import client as mqtt_client


def on_message(client, hal9000, msg):
	if msg.payload.decode('utf-8') == "init":
		hal9000.on_init()
	if msg.payload.decode('utf-8') == "wakeup":
		hal9000.on_wakeup()
	if msg.payload.decode('utf-8') == "active":
		hal9000.on_active()
	if msg.payload.decode('utf-8') == "wait":
		hal9000.on_wait()
	if msg.payload.decode('utf-8') == "sleep":
		hal9000.on_sleep()



hal9000 = HAL9000()

mqtt = mqtt_client.Client('hal9000-mqtt.py', userdata=hal9000)
mqtt.on_message = on_message
mqtt.connect("127.0.0.1", 1883)
mqtt.subscribe("hal9000/status")
mqtt.loop_start()

hal9000.loop()

