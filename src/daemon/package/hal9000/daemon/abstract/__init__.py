#!/usr/bin/python3


from configparser import ConfigParser


class HAL9000_Abstract:
	def __init__(self, name: str) -> None:
		self._name = name
	def __str__(self):
		return self._name


class HAL9000_Plugin(HAL9000_Abstract):
	def __init__(self, plugin_name) -> None:
		HAL9000_Abstract.__init__(self, plugin_name)
	def configure(self, configuration: ConfigParser, section_name: str = None) -> None:
		pass

from .daemon import HAL9000_Daemon
