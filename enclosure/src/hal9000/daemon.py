#!/usr/bin/python3

import os
import sys
import time

from configparser import ConfigParser
from paho.mqtt import client as mqtt_client

from . import HAL9000_Base

class HAL9000_Daemon(HAL9000_Base):

	STATUS_INIT = "init"
	STATUS_READY = "ready"
	STATUS_ACTIVE = "active"
	STATUS_PAUSED = "paused"
	STATUS_VALID = (STATUS_ACTIVE, STATUS_PAUSED)


	def __init__(self, name: str) -> None:
		HAL9000_Base.__init__(self, name)
		self.config = dict()
		self.mqtt = None
		self._status = HAL9000_Daemon.STATUS_INIT


	def load(self, filename: str) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip() for item in list.split(',')]})
			configuration.read(filename)
			self.configure(configuration)
			self._status = HAL9000_Daemon.STATUS_READY


	def configure(self, configuration: ConfigParser) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			HAL9000_Base.configure(self, configuration)
			self.config['daemon-delay-active'] = configuration.getfloat('daemon', 'delay-active', fallback=0.001)
			self.config['daemon-delay-paused'] = configuration.getfloat('daemon', 'delay-paused', fallback=0.100)
			self.config['mqtt-enabled'] = configuration.getboolean('daemon', 'mqtt-enabled', fallback=True)
			self.config['mqtt-client'] = configuration.get('mqtt', 'client', fallback="hal9000-daemon-{}".format(str(self)))
			self.config['mqtt-server'] = configuration.get('mqtt', 'server', fallback="127.0.0.1")
			self.config['mqtt-port'] = configuration.getint('mqtt', 'port', fallback=1883)
			self.config['mqtt-topic-base'] = configuration.get('mqtt', 'topic-base', fallback="hal9000/peripheral")



	def loop(self) -> None:
		if self.config['mqtt-enabled']:
			self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
			self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
			self.mqtt.subscribe("{}/control".format(self.config['mqtt-topic-base']))
			self.mqtt.on_message = self.on_message
			self.mqtt.loop_start()
		while self.do_loop():
			while self.status == HAL9000_Daemon.STATUS_PAUSED:
				time.sleep(self.config['daemon-delay-paused'])
			time.sleep(self.config['daemon-delay-active'])


	def on_message(self, client, userdata, message) -> None:
		if message.topic == "hal9000/{}/control".format(str(self)):
			self.status = message.payload.decode('utf-8')


	@property
	def status(self):
		return self._status


	@status.setter
	def status(self, value):
		if value in STATUS_VALID:
			self._status = value

