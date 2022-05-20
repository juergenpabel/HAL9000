#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from . import HAL9000_Device

class HAL9000_Buttons(HAL9000_Device):
	def __init__(self):
		HAL9000_Device.__init__(self, 'Buttons')
		#todo: pcf8951


	def configure(self):
		pass


	def do_loop(self):
		pass


	def on_button_pressed(self, value: float):
		print("Button={}".format(value))


	def on_button_released(self, value: float):
		print("Button={}".format(value))

