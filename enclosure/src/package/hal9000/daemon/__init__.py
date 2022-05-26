#!/usr/bin/python3

import os
import sys
import time

from configparser import ConfigParser
from paho.mqtt import client as mqtt_client

from .. import HAL9000_Base

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
			self.config['loop-delay-active'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-active', fallback=0.001)
			self.config['loop-delay-paused'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-paused', fallback=0.100)
			self.config['verbosity'] = configuration.getint('daemon:{}'.format(str(self)), 'verbosity', fallback=1)
			self.config['mqtt-enabled'] = configuration.getboolean('daemon:{}'.format(str(self)), 'mqtt-enabled', fallback=True)
			self.config['mqtt-client'] = configuration.get('mqtt', 'client', fallback="hal9000-daemon-{}".format(str(self)))
			self.config['mqtt-server'] = configuration.get('mqtt', 'server', fallback="127.0.0.1")
			self.config['mqtt-port'] = configuration.getint('mqtt', 'port', fallback=1883)
			self.config['mqtt-topic-base'] = configuration.get('mqtt', 'topic-base', fallback="hal9000/peripheral")



	def loop(self) -> None:
		if self.config['mqtt-enabled']:
			self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
			self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
			self.mqtt.subscribe("{}/control".format(self.config['mqtt-topic-base']))
			self.mqtt.on_message = self.on_mqtt
			self.mqtt.loop_start()
		delay_active = self.config['loop-delay-active']
		delay_paused = self.config['loop-delay-paused']
		while self.do_loop():
			while self.status == HAL9000_Daemon.STATUS_PAUSED:
				time.sleep(delay_paused)
			time.sleep(delay_active)


	def on_mqtt(self, client, userdata, message) -> None:
		mqtt_topic = message.topic
		mqtt_payload = message.payload.decode('utf-8')
		if self.config['verbosity'] > 0:
			print('MQTT received: {} => {}'.format(mqtt_topic, mqtt_payload))
		
		if topic == "hal9000/{}/control".format(str(self)):
			self.status = mqtt_payload


	def on_event(self, peripheral: str, device: str, event: str, value: str) -> None:
		payload = '{}:{} {}={}'.format(peripheral, device, event, value)
		if self.config['verbosity'] > 0:
			print('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_topic = '{}/event'.format(self.config['mqtt-topic-base'])
			if self.config['verbosity'] > 1:
				print('MQTT published: {} => {}'.format(mqtt_topic, payload))
			self.mqtt.publish(mqtt_topic, payload)



	@property
	def status(self):
		return self._status


	@status.setter
	def status(self, value):
		if value in STATUS_VALID:
			self._status = value

