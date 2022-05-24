#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from hal9000.device import HAL9000_Device as HAL9000

class Buttons(HAL9000):
	def __init__(self):
		HAL9000.__init__(self, 'Buttons')
		#todo: pcf8951


	def configure(self):
		pass


	def do_loop(self):
		pass


	def on_button_pressed(self, value: float):
		print("Button={}".format(value))


	def on_button_released(self, value: float):
		print("Button={}".format(value))

