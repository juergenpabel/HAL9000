#!/usr/bin/python3

import sys
import json

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from hal9000.daemon.plugin import HAL9000_Plugin


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'arduino')
		self.Devices = dict()
		self.Drivers = dict()
		self.devices = dict()
		self.drivers = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.mqtt.subscribe("hal9000/arduino:command/#")
		self.mqtt.on_message = self.on_command

		self.logger.info("Attempting to load device '{}'".format(self))
		for peripheral_name in configuration.getlist(str(self), 'peripherals'):
			module_device = configuration.getstring(peripheral_name, 'device', fallback='hal9000.arduino.device.arduino')
			if module_device not in self.Devices:
				self.logger.debug("Attempting to import device '{}'".format(module_device))
				self.Devices[module_device] = self.import_device(module_device)
			Device = self.Devices[module_device]

			module_driver = configuration.getstring(peripheral_name, 'driver', fallback='hal9000.arduino.driver.webserial')
			if module_driver not in self.Drivers:
				self.logger.debug("Attempting to import driver '{}'".format(module_driver))
				self.Drivers[module_driver] = self.import_driver(module_driver)
			Driver = self.Drivers[module_driver]

			driver = Driver(peripheral_name)
			device = Device(peripheral_name, driver)
			device.configure(configuration)
			self.devices[peripheral_name] = device
			self.drivers[peripheral_name] = driver


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, device_type: str, device_name: str, event: str, value: str=None) -> None:
		payload = '{}:{} {}={}'.format(device_type, device_name, event, value)
		self.logger.info('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_topic = 'hal9000/arduino:event/{}/{}'.format(device_type, device_name)
			self.mqtt.publish(mqtt_topic, payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, payload))


	def on_command(self, client, userdata, message) -> None:
		HAL9000.on_mqtt(self, client, userdata, message)
		command = None
		if message.topic.startswith("hal9000/arduino:command/"):
			topic = message.topic[24:]
			payload = message.payload.decode('utf-8')
			self.logger.info("COMMAND: {} => {}".format(topic, payload))
			self.drivers["rotary:volume"].send('["%s", %s]' % (topic, payload)) ## TODO

	def import_device(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Device')


	def import_driver(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Driver')

