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

	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)
		self.config = dict()
		self.mqtt = None
		self.commands = dict()
		self.logger = logging.getLogger()
		self.loop_exit = False
		signal.signal(signal.SIGHUP, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		signal.signal(signal.SIGQUIT, self.signal)
		signal.signal(signal.SIGINT, self.signal)


	def signal(self, number, frame):
		self.loop_exit = True


	def configure(self, filename: str) -> None:
		logging.config.fileConfig(filename)
		self.logger.info(f"LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"Log-level set to '{logging.getLevelName(self.logger.level)}'")
		self.configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                         'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['loop-delay-active'] = self.configuration.getfloat('daemon:brain', 'loop-delay-active', fallback=0.01)
		self.config['loop-delay-paused'] = self.configuration.getfloat('daemon:brain', 'loop-delay-paused', fallback=0.10)
		self.config['mqtt-enabled']      = self.configuration.getboolean('daemon:brain', 'mqtt-enabled', fallback=True)
		self.config['mqtt-client']       = self.configuration.getstring('mqtt', 'client', fallback='hal9000-daemon-brain')
		self.config['mqtt-server']       = str(os.getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt-port']         = int(os.getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['mqtt-loop-thread']  = self.configuration.getboolean('mqtt', 'loop-thread', fallback=True)
		self.config['mqtt-loop-timeout'] = self.configuration.getfloat('mqtt', 'loop-timeout', fallback=0.01)
		self.config['mqtt-server'] = str(os.getenv('MQTT_SERVER', default=self.config['mqtt-server']))
		self.config['mqtt-port']   = int(os.getenv('MQTT_PORT',   default=self.config['mqtt-port']))
		if self.config['mqtt-enabled']:
			self.mqtt = mqtt_client.Client(self.config['mqtt-client'])
			self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
			self.mqtt.subscribe('hal9000/command/brain/command')
			self.mqtt.on_message = self.on_mqtt
		for section_name in self.configuration.sections():
			if section_name.startswith('command:'):
				command_exec = self.configuration.getstring(section_name, 'exec', fallback=None)
				if command_exec is not None:
					command_name = section_name[8:]
					self.commands[command_name] = command_exec


	def import_plugin(self, module_name: str, class_name: str) -> HAL9000_Plugin:
		module = importlib.import_module(module_name)
		if module is not None:
			return getattr(module, class_name)
		return None


	def loop(self) -> None:
		delay_active = self.config['loop-delay-active']
		delay_paused = self.config['loop-delay-paused']
		mqtt_enabled = self.config['mqtt-enabled']
		mqtt_thread  = self.config['mqtt-loop-thread']
		mqtt_timeout = self.config['mqtt-loop-timeout']
		if mqtt_thread is True:
			self.mqtt.loop_start()
			self.mqtt._thread.name = 'MqttThread'
		try:
			while self.do_loop() is True and self.loop_exit is False:
				if mqtt_thread is False:
					self.mqtt.loop(timeout=mqtt_timeout)
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


	def on_mqtt(self, client, userdata, message) -> None:
		self.logger.debug(f"MQTT received: {message.topic} => {message.payload.decode('utf-8')}")

