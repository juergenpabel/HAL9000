#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.abstract.plugin import HAL9000_Plugin
from hal9000.peripherals.driver import HAL9000_Driver

class HAL9000_Device(HAL9000_Plugin):

	def __init__(self, name: str, Driver: HAL9000_Driver) -> None:
		HAL9000_Plugin.__init__(self, name)
		self.Driver = Driver

