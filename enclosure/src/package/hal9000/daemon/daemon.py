#!/usr/bin/python3

import time
import importlib
import logging
import logging.config

from configparser import ConfigParser
from paho.mqtt import client as mqtt_client

from hal9000.abstract import HAL9000_Abstract
from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Daemon(HAL9000_Abstract):

	STATUS_INIT = "init"
	STATUS_READY = "ready"
	STATUS_ACTIVE = "active"
	STATUS_PAUSED = "paused"


	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)
		self.config = dict()
		self.mqtt = None
		self.logger = logging.getLogger()
		self._status = HAL9000_Daemon.STATUS_INIT


	def load(self, filename: str) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
			                                                         'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
			logging.config.fileConfig(filename)
			self.logger = logging.getLogger() #TODO (str(self))
			self.logger.info('LOADING CONFIGURATION ({})'.format(filename))
			configuration.read(filename)
			self.configure(configuration)
			self._status = HAL9000_Daemon.STATUS_READY
			('READY')


	def configure(self, configuration: ConfigParser) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			self.config['loop-delay-active'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-active', fallback=0.01)
			self.config['loop-delay-paused'] = configuration.getfloat('daemon:{}'.format(str(self)), 'loop-delay-paused', fallback=0.10)
			self.config['mqtt-enabled']      = configuration.getboolean('daemon:{}'.format(str(self)), 'mqtt-enabled', fallback=True)
			self.config['mqtt-client']       = configuration.getstring('mqtt', 'client', fallback="hal9000-daemon-{}".format(str(self)))
			self.config['mqtt-server']       = configuration.getstring('mqtt', 'server', fallback="127.0.0.1")
			self.config['mqtt-port']         = configuration.getint('mqtt', 'port', fallback=1883)
			self.config['mqtt-topic-base']   = configuration.getstring('mqtt', 'topic-base', fallback="hal9000")
			self.config['mqtt-loop-thread']  = configuration.getboolean('mqtt', 'loop-thread', fallback=True)
			self.config['mqtt-loop-timeout'] = configuration.getfloat('mqtt', 'loop-timeout', fallback=0.01)
			if self.config['mqtt-enabled']:
				self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
				self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
				self.mqtt.subscribe("{}/enclosure/{}/control".format(self.config['mqtt-topic-base'], str(self)))
				self.mqtt.on_message = self.on_mqtt


	def import_plugin(self, module_name: str, class_name: str) -> HAL9000_Plugin:
		module = importlib.import_module(module_name)
		if module is not None:
			return getattr(module, class_name)
		return None


	def loop(self) -> None:
		if self.status == HAL9000_Daemon.STATUS_READY:
			delay_active = self.config['loop-delay-active']
			delay_paused = self.config['loop-delay-paused']
			mqtt_enabled = self.config['mqtt-enabled']
			mqtt_thread  = self.config['mqtt-loop-thread']
			mqtt_timeout = self.config['mqtt-loop-timeout']
			self.status = HAL9000_Daemon.STATUS_ACTIVE
			if mqtt_thread is True:
				self.mqtt.loop_start()
			self.logger.debug('LOOP')
			while self.do_loop():
				if mqtt_thread is False:
					self.mqtt.loop(timeout=mqtt_timeout)
				while self.status == HAL9000_Daemon.STATUS_PAUSED:
					time.sleep(delay_paused)
				time.sleep(delay_active)


	def on_mqtt(self, client, userdata, message) -> None:
		topic = message.topic
		payload = message.payload.decode('utf-8')
		self.logger.debug('MQTT received: {} => {}'.format(topic, payload))
		if topic == "{}/{}/control".format(self.config['mqtt-topic-base'], self):
			self.status = payload


	@property
	def status(self):
		return self._status


	@status.setter
	def status(self, value):
		if value in [HAL9000_Daemon.STATUS_ACTIVE, HAL9000_Daemon.STATUS_PAUSED]:
			self._status = value
			self.logger.debug("STATUS changed to '{}'".format(value))

