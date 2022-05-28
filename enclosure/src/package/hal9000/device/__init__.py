#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.abstract import HAL9000_Abstract


class HAL9000_Device(HAL9000_Abstract):

	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)


