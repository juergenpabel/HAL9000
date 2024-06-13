#!/usr/bin/python3

import os
import sys
import time
import importlib
import signal
import logging
import logging.config

from configparser import ConfigParser
from paho.mqtt import client as mqtt_client

from hal9000.abstract import HAL9000_Abstract
from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Daemon(HAL9000_Abstract):

	STATUS_INIT = 'init'
	STATUS_READY = 'ready'
	STATUS_ACTIVE = 'active'
	STATUS_PAUSED = 'paused'
	STATUS_EXIT = 'exit'
	STATUS_VALID = [STATUS_INIT, STATUS_READY, STATUS_ACTIVE, STATUS_PAUSED, STATUS_EXIT]


	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)
		self.config = dict()
		self.mqtt = None
		self.commands = dict()
		self.logger = logging.getLogger()
		self._status = HAL9000_Daemon.STATUS_INIT
		self.loop_exit = False
		signal.signal(signal.SIGHUP, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		signal.signal(signal.SIGQUIT, self.signal)
		signal.signal(signal.SIGINT, self.signal)


	def signal(self, number, frame):
		self.loop_exit = True


	def load(self, filename: str) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
			                                                         'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
			logging.config.fileConfig(filename)
			self.logger = logging.getLogger() #TODO (str(self))
			self.logger.info(f"LOADING CONFIGURATION '{filename}'")
			configuration.read(filename)
			self.configure(configuration)
			self.status = HAL9000_Daemon.STATUS_READY


	def configure(self, configuration: ConfigParser) -> None:
		if self.status == HAL9000_Daemon.STATUS_INIT:
			self.config['loop-delay-active'] = configuration.getfloat('daemon:brain', 'loop-delay-active', fallback=0.01)
			self.config['loop-delay-paused'] = configuration.getfloat('daemon:brain', 'loop-delay-paused', fallback=0.10)
			self.config['mqtt-enabled']      = configuration.getboolean('daemon:brain', 'mqtt-enabled', fallback=True)
			self.config['mqtt-client']       = configuration.getstring('mqtt', 'client', fallback='hal9000-daemon-brain')
			self.config['mqtt-server']       = str(os.getenv('MQTT_SERVER', default=configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
			self.config['mqtt-port']         = int(os.getenv('MQTT_PORT', default=configuration.getint('mqtt', 'port', fallback=1883)))
			self.config['mqtt-loop-thread']  = configuration.getboolean('mqtt', 'loop-thread', fallback=True)
			self.config['mqtt-loop-timeout'] = configuration.getfloat('mqtt', 'loop-timeout', fallback=0.01)
			self.config['mqtt-server'] = str(os.getenv('MQTT_SERVER', default=self.config['mqtt-server']))
			self.config['mqtt-port']   = int(os.getenv('MQTT_PORT',   default=self.config['mqtt-port']))
			if self.config['mqtt-enabled']:
				self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
				self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
				self.mqtt.subscribe('hal9000/command/brain/status')
				self.mqtt.subscribe('hal9000/command/brain/command')
				self.mqtt.on_message = self.on_mqtt
		for section_name in configuration.sections():
			if section_name.startswith('command:'):
				command_exec = configuration.getstring(section_name, 'exec', fallback=None)
				if command_exec is not None:
					command_name = section_name[8:]
					self.commands[command_name] = command_exec


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
				self.mqtt._thread.name = 'MqttThread'
			try:
				while self.do_loop() is True and self.loop_exit is False:
					if mqtt_thread is False:
						self.mqtt.loop(timeout=mqtt_timeout)
					while self.status == HAL9000_Daemon.STATUS_PAUSED:
						time.sleep(delay_paused)
					time.sleep(delay_active)
				if self.loop_exit is True:
					self.logger.info("loop() => self.loop_exit==True (probably due to a signal)")
				else:
					self.logger.info("loop() => self.do_loop() returned False (probably due to lack of heartbeat)")
			except:
				raise # TODO
				pass
			if mqtt_thread is True:
				self.mqtt.loop_stop()
			self.status = HAL9000_Daemon.STATUS_EXIT


	def on_mqtt(self, client, userdata, message) -> None:
		topic = message.topic
		payload = message.payload.decode('utf-8')
		self.logger.debug(f"MQTT received: {topic} => {payload}")
		if topic == 'hal9000/command/brain/status':
			if payload in Daemon.STATUS_VALID:
				self.status = payload
		if topic == 'hal9000/command/brain/command':
			if payload in self.commands:
				self.logger.info(f"executing configured command with id '{payload}': {self.commands[payload]}")
				os.system(self.commands[payload])


	@property
	def status(self):
		return self._status


	@status.setter
	def status(self, value):
		if value != self._status:
			if value in HAL9000_Daemon.STATUS_VALID:
				if self._status in [HAL9000_Daemon.STATUS_ACTIVE, HAL9000_Daemon.STATUS_PAUSED]:
					if value in [HAL9000_Daemon.STATUS_ACTIVE, HAL9000_Daemon.STATUS_PAUSED, HAL9000_Daemon.STATUS_EXIT]:
						self._status = value
						self.logger.debug(f"STATUS changed to '{value}'")
				else:
					self._status = value
					self.logger.debug(f"STATUS changed to '{value}'")

