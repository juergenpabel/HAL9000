#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from hal9000.device import HAL9000_Device
from driver import MFRC522

class Device(HAL9000_Device):

	def __init__(self) -> None:
		HAL9000_Device.__init__(self, "rfid")
		self.mfrc522 = MFRC522(busio.I2C(board.SCL, board.SDA), 0x28)
		self.current_uid = None


	def configure(self) -> None:
		if self.mfrc522.getReaderVersion() is None:
			self.mfrc522 = None


	def do_loop(self) -> bool:
		if self.current_uid is None:
			(status, backData, tagType) = self.mfrc522.scan()
			if status == MFRC522.MIFARE_OK:
				(status, current_uid, backBits) = self.mfrc522.identify()
				if status == MFRC522.MIFARE_OK:
					self.on_tag_enter(current_uid)
					self.current_uid = current_uid
		else:
			(status, current_uid, backBits) = self.mfrc522.identify()
			if status == MFRC522.MIFARE_OK:
				if current_uid != self.current_uid:
					self.on_tag_leave(self.current_uid)
					self.current_uid = None
					self.on_tag_enter(current_uid)
					self.current_uid = current_uid
			else:
				self.on_tag_leave(self.current_uid)
				self.current_uid = None
		return True


	def on_tag_enter(self, uid: str) -> None:
		print("Tag={} (was None)".format('-'.join(format(x, '02x') for x in uid)))


	def on_tag_leave(self, uid: str) -> None:
		print("Tag=None (was {})".format('-'.join(format(x, '02x') for x in uid)))

