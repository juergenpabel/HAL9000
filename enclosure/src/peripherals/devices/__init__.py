#!/usr/bin/python3

import os
import time

from configparser import ConfigParser
from board import *
from busio import I2C

class HAL9000_Device:

	singleton_i2c: I2C = None

	def __init__(self, name: str):
		self.name = name
		self.config = None


	@property
	def i2c(self) -> I2C:
		if HAL9000_Device.singleton_i2c is None:
			HAL9000_Device.singleton_i2c = I2C(SCL, SDA)
		return HAL9000_Device.singleton_i2c


	def configure(self, config: ConfigParser):
		self.config = config


	def do_loop(self):
		pass


	def loop(self):
		loop_interval_ms = float(self.config['DEFAULT']['loop-interval-ms']) / 1000
		while True:
			self.do_loop()
			time.sleep(loop_interval_ms)


