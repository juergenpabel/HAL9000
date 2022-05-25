#!/usr/bin/python3

import sys
from configparser import ConfigParser

from hal9000.device import HAL9000_Device as HAL9000
from hal9000.driver.mfrc522 import MFRC522 as Driver


class Device(HAL9000):

	def __init__(self, name: str) -> None:
		HAL9000.__init__(self, 'rfid:{}'.format(name))
		self.config = dict()
		self.current_uid = None
 

	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'rfid-enabled', fallback=True)
		if self.config['enabled']:
			self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
			self.driver.configure(configuration)
			if self.driver.getReaderVersion() is None:
				self.driver = None
		else:
			self.driver = None


	def do_loop(self, callback_event = None) -> bool:
		result = False
		if self.config['enabled']:
			if self.driver.do_loop():
				result = True
				previous_uid = self.current_uid
				current_uid = self.driver.current_uid
				if previous_uid != current_uid:
					self.current_uid = current_uid
					if callback_event is not None:
						peripheral, device = str(self).split(':')
						if previous_uid is not None:
							callback_event(peripheral, device, 'leave', previous_uid)
						if current_uid is not None:
							callback_event(peripheral, device, 'enter', current_uid)
		return result

