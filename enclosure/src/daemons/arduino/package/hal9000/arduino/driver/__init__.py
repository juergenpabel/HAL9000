#!/usr/bin/python3

import logging
from configparser import ConfigParser

from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Driver(HAL9000_Plugin):

	def __init__(self, name: str) -> None:
		HAL9000_Plugin.__init__(self, name)
		self.logger = logging.getLogger()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Plugin.configure(self, configuration)

