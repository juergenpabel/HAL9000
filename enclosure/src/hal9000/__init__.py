#!/usr/bin/python3

import os
import sys
import time

from configparser import ConfigParser

class HAL9000_Base:

	def __init__(self, name: str) -> None:
		self._name = name


	def configure(self, configuration: ConfigParser) -> None:
		pass


	def do_loop(self) -> bool:
		return False


	def __str__(self):
		return self._name

