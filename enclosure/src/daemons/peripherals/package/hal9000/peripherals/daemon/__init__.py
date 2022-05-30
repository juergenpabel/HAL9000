#!iusr/bin/python3

import sys

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000


class Daemon(HAL9000):

	def __init__(self, peripheral):
		HAL9000.__init__(self, peripheral)
		self.devices = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['mqtt-topic-base'] = configuration.getstring('mqtt', 'topic-base', fallback="hal9000/enclosure")
		Device = self.load_device(str(self))
		if Device is None:
			print("FATAL: loading of device '{}' failed".format(str(self)))
			sys.exit(-1)
		for name in configuration.getlist('peripheral:{}'.format(self), 'devices'):
			self.devices[name] = Device(name)
			self.devices[name].configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, peripheral: str, device: str, component: str, event: str, value: str) -> None:
		if component is None:
			component = 'default'
		payload = '{}:{}:{} {}={}'.format(peripheral, device, component, event, value)
		if self.config['verbosity'] > 0:
			print('EVENT: {}'.format(payload))
		if self.mqtt is not None:
			mqtt_base = self.config['mqtt-topic-base']
			mqtt_topic = '{}/{}/event'.format(mqtt_base, str(self))
			if self.config['verbosity'] > 1:
				print('MQTT published: {} => {}'.format(mqtt_topic, payload))
			self.mqtt.publish(mqtt_topic, payload)

