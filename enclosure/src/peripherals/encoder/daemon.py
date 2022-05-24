#!/usr/bin/python3

import sys

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from device import Device


class Daemon(HAL9000):

	def __init__(self, peripheral):
		HAL9000.__init__(self, peripheral)
		self.devices = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		for name in configuration.getlist('peripheral:{}'.format(self), 'devices'):
			self.devices[name] = Device(name)
			self.devices[name].configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


	def on_event(self, peripheral: str, device: str, event: str, value: str) -> None:
		event = '{}:{} {}={}'.format(peripheral, device, event, value)
		print(event)
		if self.mqtt:
			self.mqtt.publish('{}/event'.format(self.config['mqtt-topic-base']), event)



if __name__ == "__main__":
	daemon = Daemon('encoder')
	daemon.load(sys.argv[1])
	daemon.loop()

