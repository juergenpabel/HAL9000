#!/usr/bin/python3

import sys
import imp

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000


class Daemon(HAL9000):

	def __init__(self, peripheral):
		HAL9000.__init__(self, peripheral)
		self.devices = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		module_name = str(self)
		module_path = "hal9000/device/{}.py".format(module_name)
		Device = None
		with open(module_path, 'rb') as module_file:
			module = imp.load_module(module_name, module_file, module_path, ('py', 'r', imp.PY_SOURCE))
			Device = getattr(module, 'Device')
		if Device is not None:
			for name in configuration.getlist('peripheral:{}'.format(self), 'devices'):
				self.devices[name] = Device(name)
				self.devices[name].configure(configuration)


	def do_loop(self) -> bool:
		result = True
		for device in self.devices.values():
			result &= device.do_loop(self.on_event)
		return result


