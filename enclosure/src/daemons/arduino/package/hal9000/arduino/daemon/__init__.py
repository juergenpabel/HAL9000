#!/usr/bin/python3

import sys
import json

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from hal9000.daemon.plugin import HAL9000_Plugin


class Daemon(HAL9000):

	def __init__(self) -> None:
		HAL9000.__init__(self, 'arduino')
		self.Devices = dict()
		self.Drivers = dict()
		self.devices = dict()
		self.webserial = None


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.mqtt.subscribe("hal9000/arduino:command/#")
		self.mqtt.on_message = self.on_command
		self.logger.info("Configuring device '{}'...".format(self))
		for peripheral_name in configuration.getlist(str(self), 'peripherals'):
			module_device = configuration.getstring(peripheral_name, 'device', fallback='hal9000.arduino.device.arduino')
			if module_device not in self.Devices:
				self.logger.debug("Importing module '{}'".format(module_device))
				self.Devices[module_device] = self.import_device(module_device)
			module_driver = configuration.getstring(peripheral_name, 'driver', fallback='hal9000.arduino.driver.webserial')
			if module_driver not in self.Drivers:
				self.logger.debug("Importing module '{}'".format(module_driver))
				self.Drivers[module_driver] = self.import_driver(module_driver)
			Device = self.Devices[module_device]
			Driver = self.Drivers[module_driver]
			driver = Driver(peripheral_name)
			device = Device(peripheral_name, driver)
			self.devices[peripheral_name] = device
		if 'hal9000.arduino.driver.webserial' in self.Drivers:
			Driver = self.Drivers['hal9000.arduino.driver.webserial']
			self.webserial = Driver('driver:webserial')
			self.webserial.configure(configuration)
		for device in self.devices.values():
			device.configure(configuration)


	def loop(self) -> None:
		self.on_webserial('online')
		HAL9000.loop(self)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		if result is False:
			self.on_webserial('offline')
		return result


	def on_event(self, device_type: str, device_name: str, event: str, value: str=None) -> None:
		payload = '{}:{} {}={}'.format(device_type, device_name, event, value)
		self.logger.info('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_topic = 'hal9000/event/arduino/{}/{}'.format(device_type, device_name)
			self.mqtt.publish(mqtt_topic, payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, payload))


	def on_command(self, client, userdata, message) -> None:
		HAL9000.on_mqtt(self, client, userdata, message)
		command = None
		if message.topic.startswith("hal9000/arduino:command/"):
			topic = message.topic[24:]
			payload = message.payload.decode('utf-8')
			self.logger.info("COMMAND: {} => {}".format(topic, payload))
			self.webserial.send('["%s", %s]' % (topic, payload))


	def on_webserial(self, status: str) -> None:
		if self.mqtt is not None:
			mqtt_topic = 'hal9000/event/arduino/webserial/state'
			mqtt_payload = status
			self.mqtt.publish(mqtt_topic, mqtt_payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, mqtt_payload))


	def import_device(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Device')


	def import_driver(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Driver')

