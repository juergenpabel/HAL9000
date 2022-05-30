#!/usr/bin/python3

import os
import sys
import time

from configparser import ConfigParser
from paho.mqtt import client as mqtt_client

from hal9000.abstract import HAL9000_Abstract


class HAL9000_Daemon(HAL9000_Abstract):

	STATUS_INIT = "init"
	STATUS_READY = "ready"
	STATUS_ACTIVE = "active"
	STATUS_PAUSED = "paused"


	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)
		self.config = dict()
		self.mqtt = None
		self._status = HAL9000_Daemon.STATUS_INIT


	def load(self, filename: str) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
			                                                         'string': lambda string: string.strip('"').strip("'")})
			configuration.read(filename)
			self.configure(configuration)
			self._status = HAL9000_Daemon.STATUS_READY


	def configure(self, configuration: ConfigParser) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			HAL9000_Abstract.configure(self, configuration)
			self.config['loop-delay-active'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-active', fallback=0.001)
			self.config['loop-delay-paused'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-paused', fallback=0.100)
			self.config['verbosity'] = configuration.getint('daemon:{}'.format(str(self)), 'verbosity', fallback=1)
			self.config['mqtt-enabled'] = configuration.getboolean('daemon:{}'.format(str(self)), 'mqtt-enabled', fallback=True)
			self.config['mqtt-client'] = configuration.getstring('mqtt', 'client', fallback="hal9000-daemon-{}".format(str(self)))
			self.config['mqtt-server'] = configuration.getstring('mqtt', 'server', fallback="127.0.0.1")
			self.config['mqtt-port'] = configuration.getint('mqtt', 'port', fallback=1883)
			self.config['mqtt-topic-base'] = configuration.getstring('mqtt', 'topic-base', fallback="hal9000")
			if self.config['mqtt-enabled']:
				self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
				self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
				self.mqtt.subscribe("{}/{}/control".format(self.config['mqtt-topic-base'], str(self)))
				self.mqtt.on_message = self.on_mqtt



	def loop(self) -> None:
		if self.config['mqtt-enabled']:
			self.mqtt.loop_start()
		delay_active = self.config['loop-delay-active']
		delay_paused = self.config['loop-delay-paused']
		self._status = HAL9000_Daemon.STATUS_ACTIVE
		while self.do_loop():
			while self.status == HAL9000_Daemon.STATUS_PAUSED:
				time.sleep(delay_paused)
			time.sleep(delay_active)


	def on_mqtt(self, client, userdata, message) -> None:
		mqtt_base = self.config['mqtt-topic-base']
		mqtt_topic = message.topic
		mqtt_payload = message.payload.decode('utf-8')
		if self.config['verbosity'] > 0:
			print('MQTT received: {} => {}'.format(mqtt_topic, mqtt_payload))
		
		if message.topic == "{}/{}/control".format(mqtt_base, str(self)):
			self.status = mqtt_payload


	@property
	def status(self):
		return self._status


	@status.setter
	def status(self, value):
		if value in [HAL9000_Daemon.STATUS_ACTIVE, HAL9000_Daemon.STATUS_PAUSED]:
			self._status = value

