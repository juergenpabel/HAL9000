#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from . import HAL9000_Device


class HAL9000_RFIDReader(HAL9000_Device):
	def __init__(self):
		HAL9000_Device.__init__(self, "rfid-reader")
		i2c = busio.I2C(board.SCL, board.SDA)


	def configure(self):
		pass


	def do_loop(self):
		pass


	def on_tag_enter(self, value: str):
		print("Tag={}".format(value))


	def on_tag_leave(self, value: str):
		print("Tag=None (was {})".format(value))

