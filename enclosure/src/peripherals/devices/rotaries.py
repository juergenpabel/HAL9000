#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio
import adafruit_bus_device
import importlib
importlib.reload(board)
importlib.reload(busio)
importlib.reload(digitalio)
importlib.reload(adafruit_bus_device)

from . import HAL9000_Device
from adafruit_mcp230xx.mcp23017 import MCP23017
from drivers.mcp230xx_rotary import MCP230XX_Rotary

class HAL9000_Rotaries(HAL9000_Device):
	def __init__(self):
		HAL9000_Device.__init__(self, 'Rotaries')
		mcp = MCP23017(self.i2c, address=0x20)
		self.rotary_r = MCP230XX_Rotary(mcp, 'A', 5, 6, 7, 3, 4, board.D12)
		self.rotary_l = MCP230XX_Rotary(mcp, 'B', 0, 1, 2, 3, 4, board.D13)


	def configure(self):
		self.rotary_r.configure(5, 0, 10, False)
		self.rotary_l.configure(0, 0, 3, False)


	def do_loop(self):
		self.rotary_r.do_loop(self.on_volume, self.on_mute)
		self.rotary_l.do_loop(self.on_control, self.on_power)


	def on_volume(self, value: int):
		print("Volume={}".format(value))


	def on_mute(self, value: int):
		print("Mute={}".format(value))


	def on_control(self, value: int):
		print("Control={}".format(value))


	def on_power(self, value: int):
		print("Power={}".format(value))


