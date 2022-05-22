#!/usr/bin/python3

import time

from configparser import ConfigParser


class HAL9000_Device:

	def __init__(self, name: str) -> None:
		self.name = name
		self.config = None


	def configure(self, config: ConfigParser) -> None:
		self.config = config


	def do_loop(self) -> bool:
		return False

