#!/usr/bin/python3

#import os
import sys
#import time

#from paho.mqtt import client as mqtt_client

from device import Device as Display
from hal9000.daemon import HAL9000_Daemon as HAL9000

class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'display')
		self.display = Display()


	def configure(self, filename: str):
		HAL9000.configure(self, None)
		self.mqtt.subscribe("hal9000/display/overlay/volume")
		self.display.configure(None)


	def do_loop(self) -> bool:
		return self.display.do_loop()
	
	def on_message(self, client, userdata, message):
		if message.topic == "hal9000/display/control":
			if message.payload.decode('utf-8') == "init":
				print("init")
				self.display.on_init()
			if message.payload.decode('utf-8') == "wakeup":
				print("wakeup")
				self.display.on_wakeup()
			if message.payload.decode('utf-8') == "active":
				print("active")
				self.display.on_active()
			if message.payload.decode('utf-8') == "wait":
				self.display.on_wait()
			if message.payload.decode('utf-8') == "sleep":
				self.display.on_sleep()
		if message.topic == "hal9000/display/overlay/volume":
			if message.payload.decode('utf-8') == "show":
				self.display.on_volume_show()
			if message.payload.decode('utf-8') == "hide":
				self.display.on_volume_hide()


if __name__ == "__main__":
	daemon = Daemon()
	daemon.configure('../../../../resources/images/')
	daemon.loop()

