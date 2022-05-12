#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio


class HAL9000_Buttons:
	def __init__(self):
		i2c = busio.I2C(board.SCL, board.SDA)
		#todo: pcf8951


	def configure(self):
		pass


	def loop(self):
		while True:
			time.sleep(0.0025)


	def on_button_pressed(self, value: float):
		print("Button={}".format(value))


	def on_button_released(self, value: float):
		print("Button={}".format(value))

