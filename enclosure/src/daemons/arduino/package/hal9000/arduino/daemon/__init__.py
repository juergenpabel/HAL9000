#!iusr/bin/python3

import sys
import json

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from hal9000.daemon.plugin import HAL9000_Plugin


class Daemon(HAL9000):

	def __init__(self, arduino):
		HAL9000.__init__(self, arduino)
		self.devices = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.mqtt.subscribe("{}/system/reset".format(self.config['mqtt-topic-base']))
		self.mqtt.subscribe("{}/device/display".format(self.config['mqtt-topic-base']))
		self.mqtt.subscribe("{}/gui/screen".format(self.config['mqtt-topic-base']))
		self.mqtt.subscribe("{}/gui/overlay".format(self.config['mqtt-topic-base']))
		self.logger.info("Attempting to load device '{}'".format(str(self)))
		Device = self.import_device('hal9000.arduino.device.{}'.format(self))
		if Device is None:
			self.logger.critical("loading of device '{}' failed".format(str(self)))
			sys.exit(-1)
		for device_name in configuration.getlist('arduino:{}'.format(self), 'devices'):
			driver_name = configuration.getstring('{}:{}'.format(self,device_name), 'driver')
			self.logger.info("Attempting to load driver '{}'".format(driver_name))
			Driver = self.import_driver('hal9000.arduino.driver.{}'.format(driver_name))
			self.devices[device_name] = Device(device_name, Driver)
			self.devices[device_name].configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, device_type: str, device_name: str, event: str, value: str=None) -> None:
		payload = '{}:{} {}={}'.format(device_type, device_name, event, value)
		self.logger.info('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_base = self.config['mqtt-topic-base']
			mqtt_topic = '{}/{}/{}/event'.format(mqtt_base, device_type, device_name)
			self.mqtt.publish(mqtt_topic, payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, payload))


	def on_mqtt(self, client, userdata, message) -> None:
		HAL9000.on_mqtt(self, client, userdata, message)
		topic = message.topic
		payload = message.payload.decode('utf-8')
		if topic == "{}/system/reset".format(self.config['mqtt-topic-base']):
			self.devices["volume"].driver.send('["system/reset", %s]' % payload)
		if topic == "{}/device/display".format(self.config['mqtt-topic-base']):
			self.devices["volume"].driver.send('["device/display", %s]' % payload)
		if topic == "{}/gui/screen".format(self.config['mqtt-topic-base']):
			self.devices["volume"].driver.send('["gui/screen", %s]' % payload)
		if topic == "{}/gui/overlay".format(self.config['mqtt-topic-base']):
			self.devices["volume"].driver.send('["gui/overlay", %s]' % payload)


	def import_device(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Device')


	def import_driver(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Driver')

