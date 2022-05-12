#!/usr/bin/python3

import os
import sys
import time

from uwsgi import accepting
from paho.mqtt import client as mqtt_client

from display import Display


def on_message(client, display, msg):
	if msg.topic == "hal9000/display/control":
		if msg.payload.decode('utf-8') == "init":
			print("init")
			display.on_init()
		if msg.payload.decode('utf-8') == "wakeup":
			print("wakeup")
			display.on_wakeup()
		if msg.payload.decode('utf-8') == "active":
			print("active")
			display.on_active()
		if msg.payload.decode('utf-8') == "wait":
			display.on_wait()
		if msg.payload.decode('utf-8') == "sleep":
			display.on_sleep()
	if msg.topic == "hal9000/display/overlay/volume":
		if msg.payload.decode('utf-8') == "show":
			display.on_volume_show()
		if msg.payload.decode('utf-8') == "hide":
			display.on_volume_hide()



display = Display()
mqtt = mqtt_client.Client('hal9000-enclosure-display', userdata=display)
mqtt.on_message = on_message
mqtt.connect("127.0.0.1", 1883)
mqtt.subscribe("hal9000/display/control")
mqtt.subscribe("hal9000/display/overlay/volume")
display.configure()

accepting()

mqtt.loop_start()
display.loop()

