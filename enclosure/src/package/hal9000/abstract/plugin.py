#!/usr/bin/python3


from configparser import ConfigParser

from . import HAL9000_Abstract


class HAL9000_Plugin(HAL9000_Abstract):

	def __init__(self, plugin_name) -> None:
		HAL9000_Abstract.__init__(self, plugin_name)


	def configure(self, configuration: ConfigParser, section_name: str = None) -> None:
		pass

