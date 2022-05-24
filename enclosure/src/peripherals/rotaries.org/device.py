#!/usr/bin/python3

import board
import busio

from configparser import ConfigParser
from hal9000.device import HAL9000_Device as HAL9000

from adafruit_mcp230xx.mcp23017 import MCP23017
from driver import MCP230XX_Rotary

class Device(HAL9000):
	def __init__(self):
		HAL9000.__init__(self, 'rotaries')
		mcp = MCP23017(busio.I2C(board.SCL, board.SDA), address=0x20)
		self.rotary_r = MCP230XX_Rotary(mcp, 'A', 5, 6, 7, 3, 4, board.D12)
		self.rotary_l = MCP230XX_Rotary(mcp, 'B', 0, 1, 2, 3, 4, board.D13)


	def configure(self, config: ConfigParser):
		self.rotary_r.configure(5, 0, 10, False)
		self.rotary_l.configure(0, 0, 3, False)


	def do_loop(self) -> bool:
		self.rotary_r.do_loop(self.on_volume, self.on_mute)
		self.rotary_l.do_loop(self.on_control, self.on_power)
		return True


	def on_volume(self, value: int):
		print("Volume={}".format(value))


	def on_mute(self, value: int):
		print("Mute={}".format(value))


	def on_control(self, value: int):
		print("Control={}".format(value))


	def on_power(self, value: int):
		print("Power={}".format(value))


