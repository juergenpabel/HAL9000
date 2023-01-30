#!/usr/bin/python3

import logging
from configparser import ConfigParser

from hal9000.daemon.plugin import HAL9000_Plugin
from hal9000.arduino.driver import HAL9000_Driver


class HAL9000_Device(HAL9000_Plugin):

	def __init__(self, name: str, driver: HAL9000_Driver) -> None:
		HAL9000_Plugin.__init__(self, name)
		self.logger = logging.getLogger()
		self.driver = driver


	def configure(self, configuration: ConfigParser) -> None:
		self.driver.configure(configuration)

