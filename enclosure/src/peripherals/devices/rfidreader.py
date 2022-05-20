#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from . import HAL9000_Device
from drivers.mfrc522_i2c import *

class HAL9000_RFIDReader(HAL9000_Device):

	def __init__(self):
		HAL9000_Device.__init__(self, "RFIDReader")
		self.mfrc522 = MFRC522(self.i2c, 0x28)


	def configure(self):
		version = self.mfrc522.getReaderVersion()
		print(f'MFRC522 Software Version: {version}')
		pass


	def do_loop(self):
		pass


	def on_tag_enter(self, value: str):
		print("Tag={}".format(value))


	def on_tag_leave(self, value: str):
		print("Tag=None (was {})".format(value))

