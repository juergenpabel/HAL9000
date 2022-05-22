#!/usr/bin/python3

import os
import sys
import time

from paho.mqtt import client as mqtt_client

class HAL9000_Daemon:

	def __init__(self, name: str) -> None:
		self.device_name = name
		self.device_control = "active"


	def configure(self, filename = None) -> None:
		self.mqtt = mqtt_client.Client("hal9000-peripheral-{}".format(self.device_name))
		self.mqtt.on_message = self.on_message
		self.mqtt.connect("127.0.0.1", 1883)
		self.mqtt.subscribe("hal9000/{}/control".format(self.device_name))


	def loop(self) -> None:
		self.mqtt.loop_start()
		while self.do_loop() is True:
			while self.device_control != "active":
				time.sleep(0.1)
			time.sleep(0.001)


	def do_loop(self) -> bool:
		return False


	def on_message(self, client, userdata, message) -> None:
		if message.topic == "hal9000/{}/control".format(self.device_name):
			self.device_control = message.payload.decode('utf-8')


