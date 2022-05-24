#!/usr/bin/python3

import time
from smbus import SMBus
from configparser import ConfigParser
from . import HAL9000_Driver as HAL9000


class PCF8591(HAL9000):

	def __init__(self, name: str, debug=False):
		HAL9000.__init__(self, name)
		self.config = dict()
		self.smbus = None
		self.device = None
		self.debug = False


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['i2c-bus'] = int(configuration.get(str(self), 'i2c-bus', fallback="1"), 16)
		self.config['i2c-address'] = int(configuration.get(str(self), 'i2c-address', fallback="0x48"), 16)
		self.config['pins-sig'] = configuration.getlist(str(self), 'pins-signal')
		self.config['pins-gnd'] = configuration.getlist(str(self), 'pins-ground')
		self.smbus = SMBus(self.config['i2c-bus'])
		self.device = self.config['i2c-address']


	def do_loop(self, callback_rotary = None, callback_button = None) -> bool:
		return True

