#!/usr/bin/python3

import os
import sys
import time
import importlib.util

from configparser import ConfigParser

class HAL9000_Type:

	def __init__(self, name: str) -> None:
		self._name = name


	def __str__(self):
		return self._name



class HAL9000_Abstract(HAL9000_Type):

	MODULE_TYPES = ['Daemon', 'Device', 'Driver']


	def __init__(self, name: str) -> None:
		HAL9000_Type.__init__(self, name)
		self._module_paths = list()


	def configure(self, configuration: ConfigParser) -> None:
		self._module_paths = configuration.getlist('python', 'module_paths', fallback=['.'])


	def do_loop(self) -> bool:
		return False


	def load_device(self, name:str) -> HAL9000_Type:
		return self.__load_class('Device', name)


	def load_driver(self, name:str) -> HAL9000_Type:
		return self.__load_class('Driver', name)


	def __load_class(self, class_type: str, class_name:str) -> HAL9000_Type:
		if class_type not in HAL9000_Abstract.MODULE_TYPES:
			return None
		module_package = "hal9000.{}.{}".format(class_type.lower(), class_name.lower())
		for module_path in self._module_paths:
			module_filename = "{}/hal9000/{}/{}.py".format(module_path, class_type.lower(), class_name.lower())
			if os.path.isfile(module_filename):
				module_spec = importlib.util.spec_from_file_location(module_package, module_filename)
				module = importlib.util.module_from_spec(module_spec)
				if module is not None:
					module_spec.loader.exec_module(module)
					return getattr(module, class_type)
		return None

