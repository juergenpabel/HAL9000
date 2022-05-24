#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.device import HAL9000_Device as HAL9000
from driver import Driver


class Device(HAL9000):

	def __init__(self, name: str) -> None:
		HAL9000.__init__(self, 'rfid:{}'.format(name))
		self.driver = Driver('mfrc522:{}'.format(name))
		self.config = dict()
		self.current_uid = None
 

	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['enabled'] = configuration.getboolean(str(self), 'rfid-enabled', fallback=True)
		if self.config['enabled']:
			self.driver.configure(configuration)
			if self.driver.getReaderVersion() is None:
				self.driver = None
		else:
			self.driver = None


	def do_loop(self, callback_enter = None, callback_leave = None) -> bool:
		if self.driver is None:
			return False
		if self.driver.do_loop() is False:
			return False
		if self.current_uid != self.driver.current_uid:
			if self.current_uid is not None:
				if callback_leave is not None:
					callback_leave(self.current_uid)
			self.current_uid = self.driver.current_uid
			if self.current_uid is not None:
				if callback_enter is not None:
					callback_enter(self.current_uid)
		return True

