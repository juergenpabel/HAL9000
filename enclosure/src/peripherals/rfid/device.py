#!/usr/bin/python3

import os
import time

import board
import busio
import digitalio

from hal9000.device import HAL9000_Device
from driver import MFRC522

class Device(HAL9000_Device):

	def __init__(self, smbus, address) -> None:
		HAL9000_Device.__init__(self, "rfid")
		self.mfrc522 = MFRC522(smbus, address)
		self.current_uid = None
		self.callback_enter = self.on_tag_enter
		self.callback_leave = self.on_tag_leave


	def configure(self, callback_enter, callback_leave) -> None:
		if self.mfrc522.getReaderVersion() is None:
			self.mfrc522 = None
		if callback_enter is not None:
			self.callback_enter = callback_enter
		if callback_leave is not None:
			self.callback_leave = callback_leave


	def do_loop(self) -> bool:
		if self.mfrc522 is None:
			return False
		if self.current_uid is None:
			(status, backData, tagType) = self.mfrc522.scan()
			if status == MFRC522.MIFARE_OK:
				(status, current_uid, backBits) = self.mfrc522.identify()
				current_uid = ''.join(format(x, '02x') for x in current_uid)
				if status == MFRC522.MIFARE_OK:
					self.callback_enter(current_uid)
					self.current_uid = current_uid
		else:
			(status, current_uid, backBits) = self.mfrc522.identify()
			current_uid = ''.join(format(x, '02x') for x in current_uid)
			if status == MFRC522.MIFARE_OK:
				if current_uid != self.current_uid:
					self.callback_leave(self.current_uid)
					self.current_uid = None
					self.callback_enter(current_uid)
					self.current_uid = current_uid
			else:
				self.callback_leave(self.current_uid)
				self.current_uid = None
		return True


	def on_tag_enter(self, uid: str) -> None:
		print("Tag={} (was None)".format(uid))


	def on_tag_leave(self, uid: str) -> None:
		print("Tag=None (was {})".format(uid))

