#!/usr/bin/python3

import sys
from configparser import ConfigParser

from hal9000.device import HAL9000_Device as HAL9000


class Device(HAL9000):

	def __init__(self, name: str) -> None:
		HAL9000.__init__(self, 'rfid:{}'.format(name))
		self.config = dict()
		self.driver = None
		self.current_uid = None
 

	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'rfid-enabled', fallback=True)
		if self.config['enabled']:
			Driver = self.load_driver(configuration.getstring(str(self), 'driver'))
			self.driver = Driver('{}:{}'.format(configuration.getstring(str(self), 'driver'), device))
			self.driver.configure(configuration)
			if self.driver.getReaderVersion() is None:
				self.driver = None


	def do_loop(self, callback_event = None) -> bool:
		result = False
		if self.driver is not None:
			if self.driver.do_loop():
				result = True
				previous_uid = self.current_uid
				current_uid = self.driver.current_uid
				if previous_uid != current_uid:
					self.current_uid = current_uid
					if callback_event is not None:
						peripheral, device = str(self).split(':',1)
						component, dummy = str(self.driver).split(':',1)
						if previous_uid is not None:
							callback_event(peripheral, device, component, 'leave', previous_uid)
						if current_uid is not None:
							callback_event(peripheral, device, component, 'enter', current_uid)
 
		return result

