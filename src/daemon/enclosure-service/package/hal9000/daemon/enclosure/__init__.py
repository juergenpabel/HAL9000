#!/usr/bin/python3

import sys
import json

from configparser import ConfigParser

from hal9000.daemon.abstract import HAL9000_Daemon as HAL9000
from hal9000.daemon.abstract import HAL9000_Plugin


class Daemon(HAL9000):

	def __init__(self) -> None:
		HAL9000.__init__(self, 'enclosure')
		self.Devices = dict()
		self.Drivers = dict()
		self.devices = dict()
		self.webserial = None


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.mqtt.subscribe("hal9000/daemon/enclosure-service/#")
		self.mqtt.on_message = self.on_command
		self.logger.info("Configuring device '{}'...".format(self))
		for peripheral_name in configuration.getlist(str(self), 'peripherals'):
			module_device = configuration.getstring(peripheral_name, 'device', fallback='hal9000.daemon.enclosure.device.arduino')
			if module_device not in self.Devices:
				self.logger.debug("Importing module '{}'".format(module_device))
				self.Devices[module_device] = self.import_device(module_device)
			module_driver = configuration.getstring(peripheral_name, 'driver', fallback='hal9000.daemon.enclosure.driver.webserial')
			if module_driver not in self.Drivers:
				self.logger.debug("Importing module '{}'".format(module_driver))
				self.Drivers[module_driver] = self.import_driver(module_driver)
			Device = self.Devices[module_device]
			Driver = self.Drivers[module_driver]
			driver = Driver(peripheral_name)
			device = Device(peripheral_name, driver)
			self.devices[peripheral_name] = device
		if 'hal9000.daemon.enclosure.driver.webserial' in self.Drivers:
			Driver = self.Drivers['hal9000.daemon.enclosure.driver.webserial']
			self.webserial = Driver('driver:webserial')
			self.webserial.configure(configuration)
		for device in self.devices.values():
			device.configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, device_type: str, device_name: str, event: str, value: str=None) -> None:
		payload = '{}:{} {}={}'.format(device_type, device_name, event, value)
		self.logger.info('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_topic = 'hal9000/daemon/enclosure-service/event/{}:{}'.format(device_type, device_name)
			self.mqtt.publish(mqtt_topic, payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, payload))


	def on_command(self, client, userdata, message) -> None:
		HAL9000.on_mqtt(self, client, userdata, message)
		if self.webserial is None:
			self.logger.error(f"COMMAND '{message.topic}' received, but webserial connection not established")
			return
		if message.topic.startswith("hal9000/daemon/enclosure-service/command/"):
			topic = message.topic[41:]
			payload = message.payload.decode('utf-8')
			self.logger.info("COMMAND: {} => {}".format(topic, payload))
			self.webserial.send('["%s", %s]' % (topic, payload))


	def import_device(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Device')


	def import_driver(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Driver')

