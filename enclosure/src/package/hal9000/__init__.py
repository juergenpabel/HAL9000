#!/usr/bin/python3

import os
import sys
import time
import importlib.util

from configparser import ConfigParser

class HAL9000_Abstract:
	pass


class HAL9000_Base(HAL9000_Abstract):

	MODULE_TYPES = ['Daemon', 'Device', 'Driver']

	def __init__(self, name: str) -> None:
		self._name = name
		self._module_paths = list()


	def configure(self, configuration: ConfigParser) -> None:
		self._module_paths = configuration.getlist('python', 'module_paths', fallback=['.'])


	def do_loop(self) -> bool:
		return False


	def load_device(self, name:str) -> HAL9000_Abstract:
		return self.__load_class('Device', name)


	def load_driver(self, name:str) -> HAL9000_Abstract:
		return self.__load_class('Driver', name)


	def __load_class(self, class_type: str, class_name:str) -> HAL9000_Abstract:
		if class_type not in HAL9000_Base.MODULE_TYPES:
			return None
		module_package = "hal9000.{}.{}".format(class_type.lower(), class_name.lower())
		for module_path in self._module_paths:
			module_path = module_path.strip('"').strip("'")
			module_filename = "{}/hal9000/{}/{}.py".format(module_path, class_type.lower(), class_name.lower())
			if os.path.isfile(module_filename):
				module_spec = importlib.util.spec_from_file_location(module_package, module_filename)
				module = importlib.util.module_from_spec(module_spec)
				if module is not None:
					module_spec.loader.exec_module(module)
					return getattr(module, class_type)
		return None


	def __str__(self):
		return self._name

