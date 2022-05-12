#!/usr/bin/python3

import os
import time

from configparser import ConfigParser

from .rfidreader import HAL9000_RFIDReader
from .rotaries import HAL9000_Rotaries
from .buttons import HAL9000_Buttons

class HAL9000_Device:

	def __init__(self, name: str):
		self.name = name
		self.config = None


	def configure(self, config: ConfigParser):
		self.config = config
		pass


	def do_loop(self):
		pass


	def loop(self):
		loop_interval_ms = float(self.config['DEFAULT']['loop-interval-ms']) / 1000
		while True:
			self.do_loop()
			time.sleep(loop_interval_ms)


