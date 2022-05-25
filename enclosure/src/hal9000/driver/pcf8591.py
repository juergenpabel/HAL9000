#!/usr/bin/python3

import time
from smbus import SMBus
from configparser import ConfigParser
from . import HAL9000_Driver as HAL9000


class PCF8591(HAL9000):

	CHANNEL_OUT = 0x40

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
		self.config['enable-out'] = configuration.getboolean(str(self), 'enable-out', fallback=True)
		self.smbus = SMBus(self.config['i2c-bus'])
		self.device = self.config['i2c-address']
		out_level = 0x00
		if self.config['enable-out']:
			out_level = 0xff
		self.write(PCF8591.CHANNEL_OUT, out_level)
		self.cache = list()
		for channel in range(0, 4):
			self.cache.append(0)


	def do_loop(self, callback_event = None) -> bool:
		for channel in range(0, 4):
			self.cache[channel] = self.read(channel)
		return True


	def read(self, channel: int) -> int:
		write_channel = 0x00
		write_command = 0x00
		if self.config['enable-out']:
			write_channel = PCF8591.CHANNEL_OUT
			write_command = 0xff
		write_channel |= channel & 0x03
		result = self.write(write_channel, write_command)
		# i2c reads are started on the ACK of the WRITE and
		# not returned until the read after the _next_ WRITE
		# so we have to do it twice to get the actual value
		result = self.write(write_channel, write_command)
		return result


	def write(self, channel: int, command: int) -> int:
		self.smbus.write_byte_data(self.device, channel, command)
		return self.smbus.read_byte(self.device)


	def channel(self, channel) -> int:
		return self.cache[channel]

