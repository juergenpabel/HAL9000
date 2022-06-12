#!iusr/bin/python3

import sys

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from hal9000.daemon.plugin import HAL9000_Plugin


class Daemon(HAL9000):

	def __init__(self, peripheral):
		HAL9000.__init__(self, peripheral)
		self.devices = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['mqtt-topic-base'] = configuration.getstring('mqtt', 'topic-base', fallback="hal9000/enclosure")
		self.logger.info("Attempting to load device '{}'".format(str(self)))
		Device = self.import_device('hal9000.peripherals.device.{}'.format(self))
		if Device is None:
			self.logger.critical("loading of device '{}' failed".format(str(self)))
			sys.exit(-1)
		for device_name in configuration.getlist('peripheral:{}'.format(self), 'devices'):
			driver_name = configuration.getstring('{}:{}'.format(self,device_name), 'driver')
			self.logger.info("Attempting to load driver '{}'".format(driver_name))
			Driver = self.import_driver('hal9000.peripherals.driver.{}'.format(driver_name))
			self.devices[device_name] = Device(device_name, Driver)
			self.devices[device_name].configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, peripheral: str, device: str, component: str, event: str, value: str) -> None:
		if component is None:
			component = 'default'
		payload = '{}:{}:{} {}={}'.format(peripheral, device, component, event, value)
		self.logger.debug('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_base = self.config['mqtt-topic-base']
			mqtt_topic = '{}/{}/event'.format(mqtt_base, str(self))
			self.mqtt.publish(mqtt_topic, payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, payload))


	def import_device(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Device')


	def import_driver(self, module_name:str) -> HAL9000_Plugin:
		return self.import_plugin(module_name, 'Driver')

