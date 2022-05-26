#!/usr/bin/python3

from configparser import ConfigParser

from .. import HAL9000_Base


class HAL9000_Device(HAL9000_Base):

	def __init__(self, name: str) -> None:
		HAL9000_Base.__init__(self, name)


